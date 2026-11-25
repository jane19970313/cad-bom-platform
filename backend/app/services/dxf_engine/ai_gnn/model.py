from __future__ import annotations

import torch
from torch import nn
import torch.nn.functional as F
from torch_geometric.utils import softmax


def _edge_key(edge_type):
    return "|".join(str(part) for part in edge_type)


class RelationMatchingNetwork(nn.Module):
    """Relation-specific edge-aware message and attention score."""

    def __init__(self, hidden_channels: int, edge_channels: int):
        super().__init__()
        self.source = nn.Linear(hidden_channels, hidden_channels, bias=False)
        self.edge = nn.Linear(max(1, edge_channels), hidden_channels, bias=False)
        self.score = nn.Sequential(
            nn.Linear(hidden_channels * 2, hidden_channels // 2 or 1),
            nn.LeakyReLU(0.1),
            nn.Linear(hidden_channels // 2 or 1, 1),
        )

    def forward(self, source_x, edge_attr):
        if edge_attr is None or edge_attr.size(-1) == 0:
            edge_attr = source_x.new_zeros((source_x.size(0), self.edge.in_features))
        projected_source = self.source(source_x)
        message = torch.tanh(projected_source + self.edge(edge_attr))
        score = self.score(torch.cat([message, projected_source], dim=-1))
        return message, score


class HeterogeneousMessagePassing(nn.Module):
    """Destination-normalized attention across all incoming typed relations.

    Unlike independent sigmoid gates, incoming edges compete in one softmax
    for each destination node. Relation modules use stable numeric keys, so
    punctuation in a relation name cannot create ModuleDict key collisions.
    """

    def __init__(self, node_types, edge_types, hidden_channels, edge_dims, dropout=0.2):
        super().__init__()
        self.node_types = list(node_types)
        self.edge_types = list(edge_types)
        self.edge_keys = {edge_type: f"relation_{i}" for i, edge_type in enumerate(self.edge_types)}
        self.messages = nn.ModuleDict()
        for edge_type in self.edge_types:
            width = int(edge_dims.get(_edge_key(edge_type), 1))
            self.messages[self.edge_keys[edge_type]] = RelationMatchingNetwork(hidden_channels, width)
        self.updates = nn.ModuleDict({
            node_type: nn.Sequential(
                nn.Linear(hidden_channels * 2, hidden_channels),
                nn.GELU(), nn.Dropout(dropout),
                nn.Linear(hidden_channels, hidden_channels),
            ) for node_type in self.node_types
        })
        self.norms = nn.ModuleDict({n: nn.LayerNorm(hidden_channels) for n in self.node_types})
        self.dropout = dropout

    def forward(self, x_dict, data):
        incoming = {n: {"messages": [], "scores": [], "indices": []} for n in x_dict}
        for edge_type in self.edge_types:
            if edge_type not in data.edge_types:
                continue
            store = data[edge_type]
            edge_index = getattr(store, "edge_index", None)
            if edge_index is None or edge_index.numel() == 0:
                continue
            src_type, _, dst_type = edge_type
            src, dst = edge_index[0], edge_index[1]
            edge_attr = getattr(store, "edge_attr", None)
            message_mask = getattr(store, "message_passing_mask", None)
            if message_mask is not None:
                message_mask = message_mask.to(device=src.device, dtype=torch.bool)
                if not bool(message_mask.any()):
                    continue
                src, dst = src[message_mask], dst[message_mask]
                if edge_attr is not None:
                    edge_attr = edge_attr[message_mask]
            message, score = self.messages[self.edge_keys[edge_type]](
                x_dict[src_type][src], edge_attr
            )
            incoming[dst_type]["messages"].append(message)
            incoming[dst_type]["scores"].append(score)
            incoming[dst_type]["indices"].append(dst)

        updated = {}
        for node_type, current in x_dict.items():
            bucket = incoming[node_type]
            if bucket["messages"]:
                messages = torch.cat(bucket["messages"], dim=0)
                scores = torch.cat(bucket["scores"], dim=0)
                indices = torch.cat(bucket["indices"], dim=0)
                weights = softmax(scores, indices, num_nodes=current.size(0))
                aggregate = current.new_zeros(current.shape)
                aggregate.index_add_(0, indices, messages * weights)
            else:
                aggregate = current.new_zeros(current.shape)
            delta = self.updates[node_type](torch.cat([current, aggregate], dim=-1))
            updated[node_type] = F.dropout(
                F.gelu(self.norms[node_type](current + delta)),
                p=self.dropout, training=self.training,
            )
        return updated


class GeometricReasoningNetwork(nn.Module):
    """Cross-node-type reasoning after typed message passing.

    Stacked heterogeneous layers explicitly support multi-hop paths such as
    Dimension -> Anchor -> Geometry. This layer then reasons over the fused
    evidence at each node without collapsing relation types prematurely.
    """

    def __init__(self, node_types, hidden_channels, dropout=0.2):
        super().__init__()
        self.reasoners = nn.ModuleDict({
            n: nn.Sequential(
                nn.Linear(hidden_channels, hidden_channels * 2), nn.GELU(),
                nn.Dropout(dropout), nn.Linear(hidden_channels * 2, hidden_channels),
                nn.LayerNorm(hidden_channels),
            ) for n in node_types
        })
        self.dropout = dropout

    def forward(self, x_dict):
        return {
            n: F.dropout(x + self.reasoners[n](x), p=self.dropout, training=self.training)
            for n, x in x_dict.items()
        }


class DXFSemanticGNN(nn.Module):
    """Relation-aware multi-task DXF GNN.

    Returns class logits, fused log1p measurements, node embeddings, and
    direct/relation/fusion evidence for explainable downstream inference.
    All regression branches are non-negative by construction.
    """

    def __init__(
        self, metadata, input_dims: dict[str, int],
        edge_dims: dict[str, int] | None = None,
        hidden_channels: int = 96, num_classes: int = 8,
        num_layers: int = 3, dropout: float = 0.20,
    ):
        super().__init__()
        self.node_types, self.edge_types = metadata
        edge_dims = edge_dims or {}
        self.input_proj = nn.ModuleDict({
            n: nn.Sequential(nn.Linear(input_dims[n], hidden_channels),
                             nn.LayerNorm(hidden_channels), nn.GELU())
            for n in self.node_types
        })
        self.message_layers = nn.ModuleList([
            HeterogeneousMessagePassing(
                self.node_types, self.edge_types, hidden_channels,
                edge_dims, dropout,
            ) for _ in range(max(2, num_layers))
        ])
        self.relation_reasoner = GeometricReasoningNetwork(
            self.node_types, hidden_channels, dropout
        )
        self.classifier = nn.Sequential(
            nn.Linear(hidden_channels, hidden_channels), nn.GELU(),
            nn.Dropout(dropout), nn.Linear(hidden_channels, num_classes),
        )
        self.direct_head = nn.Sequential(
            nn.Linear(hidden_channels, hidden_channels), nn.GELU(),
            nn.Dropout(dropout), nn.Linear(hidden_channels, 2),
        )
        self.relation_head = nn.Sequential(
            nn.Linear(hidden_channels, hidden_channels), nn.GELU(),
            nn.Dropout(dropout), nn.Linear(hidden_channels, 2),
        )
        self.fusion_head = nn.Sequential(
            nn.Linear(hidden_channels, hidden_channels // 2 or 1),
            nn.GELU(), nn.Linear(hidden_channels // 2 or 1, 2),
        )
        self.text_match_edge_types = [
            edge_type for edge_type in self.edge_types
            if edge_type[0] == "text" and edge_type[2] == "geometry"
            and edge_type[1] in {
                "dimension_value_candidate", "part_label_candidate",
                "geometry_description_candidate", "gdt_candidate",
                "reviewed_match_candidate",
            }
        ]
        self.text_match_keys = {
            edge_type: f"text_match_{index}"
            for index, edge_type in enumerate(self.text_match_edge_types)
        }
        self.text_match_heads = nn.ModuleDict()
        for edge_type in self.text_match_edge_types:
            edge_width = max(1, int(edge_dims.get(_edge_key(edge_type), 1)))
            self.text_match_heads[self.text_match_keys[edge_type]] = nn.Sequential(
                nn.Linear(hidden_channels * 2 + edge_width, hidden_channels),
                nn.GELU(), nn.Dropout(dropout),
                nn.Linear(hidden_channels, hidden_channels // 2 or 1),
                nn.GELU(), nn.Linear(hidden_channels // 2 or 1, 1),
            )

    def forward(self, data):
        x_dict = {n: self.input_proj[n](data[n].x) for n in self.node_types}
        # Local geometry-only representation is retained for the direct baseline.
        geometry_local = x_dict["geometry"]
        for layer in self.message_layers:
            x_dict = layer(x_dict, data)
        x_dict = self.relation_reasoner(x_dict)
        geometry_relation = x_dict["geometry"]
        class_logits = self.classifier(geometry_relation)

        # Direct branch sees local geometry only; relation branch sees the
        # Dimension/Anchor/Text/Geometry message-passing result.
        # Learned outputs are non-curve length and radius; CIRCLE/ARC length
        # is derived deterministically from the predicted radius and sweep.
        direct_raw = F.softplus(self.direct_head(geometry_local))  # [length, radius]
        relation_raw = F.softplus(self.relation_head(geometry_relation))
        fusion = torch.sigmoid(self.fusion_head(geometry_relation))
        fused_two = fusion * direct_raw + (1.0 - fusion) * relation_raw

        # CIRCLE/ARC length is deterministic once radius is predicted. For an
        # ARC, arc_sweep_angle_rad comes from the original DXF start/end angles
        # (or the graph builder's geometric fallback). Other entities retain
        # learned length regression.
        entity_types = [
            str(value).upper()
            for value in getattr(data["geometry"], "entity_type", ["OTHER"] * fused_two.size(0))
        ]
        circle_mask = torch.tensor(
            [value == "CIRCLE" for value in entity_types],
            dtype=torch.bool, device=fused_two.device,
        )
        arc_mask = torch.tensor(
            [value == "ARC" for value in entity_types],
            dtype=torch.bool, device=fused_two.device,
        )
        sweep_values = torch.as_tensor(
            getattr(data["geometry"], "arc_sweep_angle_rad", [0.0] * fused_two.size(0)),
            dtype=fused_two.dtype, device=fused_two.device,
        ).reshape(-1)
        sweep_values = torch.where(
            circle_mask, torch.full_like(sweep_values, 2.0 * torch.pi), sweep_values
        ).clamp(min=0.0, max=2.0 * torch.pi)
        deterministic_length_mask = circle_mask | (arc_mask & (sweep_values > 1e-9))

        def length_from_radius(learned_length, predicted_radius):
            derived_length = predicted_radius * sweep_values
            return torch.where(deterministic_length_mask, derived_length, learned_length)

        direct_length = length_from_radius(direct_raw[:, 0], direct_raw[:, 1])
        relation_length = length_from_radius(relation_raw[:, 0], relation_raw[:, 1])
        fused_length = length_from_radius(fused_two[:, 0], fused_two[:, 1])

        # Area is not independently regressed. It is derived from raw Shapely
        # shape area/perimeter and the corrected length prediction. Reviewed
        # area labels supervise this derived estimate through length/radius.
        raw_area = torch.as_tensor(
            getattr(data["geometry"], "raw_geometry_area", [0.0] * fused_two.size(0)),
            dtype=fused_two.dtype, device=fused_two.device,
        ).reshape(-1)
        raw_perimeter = torch.as_tensor(
            getattr(data["geometry"], "raw_geometry_perimeter", [0.0] * fused_two.size(0)),
            dtype=fused_two.dtype, device=fused_two.device,
        ).reshape(-1)
        safe_perimeter = raw_perimeter.clamp_min(1e-8)
        def area_from_predictions(length_values, radius_values):
            polygon_area = raw_area * (length_values / safe_perimeter).square()
            polygon_valid = (raw_area > 0.0) & (raw_perimeter > 1e-8)
            circle_area = torch.pi * radius_values.square()
            return torch.where(
                circle_mask,
                circle_area,
                torch.where(polygon_valid, polygon_area, torch.zeros_like(polygon_area)),
            )

        direct_area = area_from_predictions(direct_length, direct_raw[:, 1])
        relation_area = area_from_predictions(relation_length, relation_raw[:, 1])
        derived_area = area_from_predictions(fused_length, fused_two[:, 1])
        # Keep the established public output ordering [length, area, radius].
        fused_raw = torch.stack([fused_length, derived_area, fused_two[:, 1]], dim=-1)
        direct_log = torch.stack([
            torch.log1p(direct_length),
            torch.log1p(direct_area),
            torch.log1p(direct_raw[:, 1]),
        ], dim=-1)
        relation_log = torch.stack([
            torch.log1p(relation_length),
            torch.log1p(relation_area),
            torch.log1p(relation_raw[:, 1]),
        ], dim=-1)
        text_match_logits = {}
        for edge_type in self.text_match_edge_types:
            store = data[edge_type]
            edge_index = getattr(store, "edge_index", None)
            if edge_index is None or edge_index.numel() == 0:
                text_match_logits[edge_type] = geometry_relation.new_empty((0,))
                continue
            src, dst = edge_index[0], edge_index[1]
            edge_attr = getattr(store, "edge_attr", None)
            edge_width = self.text_match_heads[self.text_match_keys[edge_type]][0].in_features - 2 * geometry_relation.size(-1)
            if edge_attr is None or edge_attr.size(-1) == 0:
                edge_attr = geometry_relation.new_zeros((src.numel(), edge_width))
            # The final edge feature marks a reviewed pair that had to be
            # injected after candidate generation. It is diagnostic metadata,
            # never a model input: otherwise the positive target would leak.
            match_edge_attr = edge_attr
            if edge_attr is not None and edge_attr.size(-1) >= 39:
                match_edge_attr = edge_attr.clone()
                match_edge_attr[:, 38] = 0.0
            match_input = torch.cat([
                x_dict["text"][src], geometry_relation[dst], match_edge_attr,
            ], dim=-1)
            text_match_logits[edge_type] = self.text_match_heads[
                self.text_match_keys[edge_type]
            ](match_input).squeeze(-1)

        evidence = {
            "direct_log": direct_log,
            "relation_log": relation_log,
            "fusion_weight": torch.stack(
                [fusion[:, 0], fusion[:, 0], fusion[:, 1]], dim=-1
            ),
            "direct_raw": torch.stack([direct_raw[:, 0], direct_area, direct_raw[:, 1]], dim=-1),
            "relation_raw": torch.stack([relation_raw[:, 0], relation_area, relation_raw[:, 1]], dim=-1),
            "fused_raw": fused_raw,
            "area_is_derived": True,
            "circle_arc_length_is_derived": True,
            "arc_sweep_angle_rad": sweep_values,
            "deterministic_length_mask": deterministic_length_mask,
            "text_match_logits": text_match_logits,
        }
        return class_logits, torch.log1p(fused_raw), x_dict, evidence
