from __future__ import annotations

import csv
import json
import math
from pathlib import Path
import torch

from .geometry_features import GEOMETRY_FEATURE_NAMES
from .graph_builder import TEXT_FEATURE_NAMES


def _read_label_rows(path: str | Path):
    path = Path(path)
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            return list(csv.DictReader(stream))
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        rows = []
        for handle, value in payload.items():
            if isinstance(value, dict):
                rows.append({"source_handle": handle, **value})
            else:
                rows.append({"source_handle": handle, "label": value})
        return rows
    if not isinstance(payload, list):
        raise ValueError("Labels JSON must be an object or a list of records.")
    return payload


def load_handle_labels(path: str | Path) -> dict[str, str]:
    """Load optional geometry classification labels keyed by DXF handle."""
    result = {}
    for row in _read_label_rows(path):
        handle = row.get("source_handle") or row.get("handle")
        label = row.get("label") or row.get("class")
        if handle and label:
            result[str(handle).strip()] = str(label).strip()
    return result


def load_geometry_targets(path: str | Path) -> dict[str, dict[str, float]]:
    """Load reviewed independent measurement targets from CSV or JSON.

    Expected columns/keys: source_handle,length,area,radius.
    Do NOT populate these columns from the existing analytical geometry
    length/area if the goal is to train an independent AI estimator.
    Blank fields are treated as unavailable targets.
    """
    targets = {}
    for row in _read_label_rows(path):
        handle = row.get("source_handle") or row.get("handle")
        if not handle:
            continue
        values = {}
        for name in ("length", "area", "radius"):
            raw = row.get(name)
            if raw in (None, ""):
                continue
            try:
                value = float(raw)
            except (TypeError, ValueError, OverflowError):
                continue
            if math.isfinite(value) and value >= 0.0:
                values[name] = value
        if values:
            targets[str(handle).strip()] = values
    return targets


def attach_labels(data, handle_labels: dict[str, str], class_to_id: dict[str, int]):
    """Attach reviewed geometry classification labels; unlabeled nodes are masked."""
    handles = data["geometry"].source_handle
    y = [-100] * len(handles)
    mask = [False] * len(handles)
    for index, handle in enumerate(handles):
        label = handle_labels.get(str(handle))
        if label is not None and label in class_to_id:
            y[index] = int(class_to_id[label])
            mask[index] = True
    data["geometry"].y = torch.tensor(y, dtype=torch.long)
    data["geometry"].class_mask = torch.tensor(mask, dtype=torch.bool)
    # Backward-compatible alias used by the original classifier-label workflow.
    data["geometry"].train_mask = data["geometry"].class_mask.clone()
    return data


def load_text_geometry_labels(path: str | Path) -> dict[tuple[str, str, str], int]:
    """Load reviewed text-to-geometry correspondences from CSV/JSON rows.

    Required fields: text_handle, geometry_handle, is_match.
    Optional relation_type is a semantic candidate relation name; '*' labels
    every semantic relation for that text/geometry pair.
    """
    result = {}
    for row in _read_label_rows(path):
        text_handle = row.get("text_handle")
        geometry_handle = row.get("geometry_handle")
        raw_match = row.get("is_match")
        if not text_handle or not geometry_handle or raw_match in (None, ""):
            continue
        value = str(raw_match).strip().lower()
        if value in {"1", "true", "yes", "y", "match", "positive"}:
            label = 1
        elif value in {"0", "false", "no", "n", "nonmatch", "negative"}:
            label = 0
        else:
            continue
        relation = str(row.get("relation_type") or "*").strip()
        result[(str(text_handle).strip(), str(geometry_handle).strip(), relation)] = label
    return result


def _text_geometry_relations_for_label(data, text_index: int, requested_relation: str):
    supported = {
        "dimension_value_candidate", "part_label_candidate",
        "geometry_description_candidate", "gdt_candidate",
    }
    if requested_relation in supported:
        return [requested_relation]
    semantic_types = getattr(data["text"], "semantic_types", None)
    if semantic_types is not None and text_index < len(semantic_types):
        categories = [str(value).upper() for value in semantic_types[text_index]]
    else:
        primary = getattr(data["text"], "semantic_type", [])
        categories = [str(primary[text_index]).upper()] if text_index < len(primary) else ["UNKNOWN"]
    relation_map = {
        "DIMENSION_VALUE": "dimension_value_candidate",
        "PART_LABEL": "part_label_candidate",
        "GEOMETRY_DESCRIPTION": "geometry_description_candidate",
        "TOLERANCE_GDT": "gdt_candidate",
    }
    relations = list(dict.fromkeys(
        relation_map[category] for category in categories if category in relation_map
    ))
    return relations or ["reviewed_match_candidate"]


def _reviewed_edge_features(data, text_index: int, geometry_index: int):
    """Build an approximate edge descriptor for a reviewed pair omitted by
    candidate generation. The override bit is diagnostic only and is masked
    from the matcher; the edge is excluded from message passing."""
    text_x = data["text"].x[text_index]
    geom_x = data["geometry"].x[geometry_index]
    tx, ty = float(text_x[0]), float(text_x[1])
    gx, gy = float(geom_x[0]), float(geom_x[1])
    text_width = max(0.0, float(text_x[2]))
    text_height = max(0.0, float(text_x[3]))
    geom_width = max(0.0, float(geom_x[2]))
    geom_height = max(0.0, float(geom_x[3]))
    center_distance = math.hypot(tx - gx, ty - gy)
    bbox_dx = max(0.0, abs(tx - gx) - 0.5 * (text_width + geom_width))
    bbox_dy = max(0.0, abs(ty - gy) - 0.5 * (text_height + geom_height))
    bbox_distance = math.hypot(bbox_dx, bbox_dy)
    scale = max(float(data.graph_metadata.get("scale", 1.0)), 1e-9)

    geometry_type = (
        str(data["geometry"].geometry_type[geometry_index]).upper()
        if hasattr(data["geometry"], "geometry_type") else "OTHER"
    )
    entity_type = (
        str(data["geometry"].entity_type[geometry_index]).upper()
        if hasattr(data["geometry"], "entity_type") else "OTHER"
    )
    geom_type_names = (
        "CLOSED_PROFILE", "LINEAR_GEOMETRY", "POINT", "OTHER",
        "UNKNOWN", "POLYGON", "LINESTRING", "MULTILINESTRING",
    )
    attrs = [0.0] * 39
    attrs[0] = bbox_distance
    attrs[1] = center_distance
    attrs[2] = center_distance
    attrs[3] = 0.5 * bbox_distance + 0.5 * center_distance
    attrs[4] = 1.0 / (1.0 + attrs[3])
    attrs[5] = 1.0 if entity_type in {"CIRCLE", "ARC"} else 0.65

    has_diameter = bool(getattr(data["text"], "has_diameter_symbol", [False])[text_index])
    has_radius = bool(getattr(data["text"], "has_radius_symbol", [False])[text_index])
    diameter = getattr(data["text"], "diameter_value", [])
    radius = getattr(data["text"], "radius_value", [])
    dvalue = float(diameter[text_index]) if text_index < len(diameter) else float("nan")
    rvalue = float(radius[text_index]) if text_index < len(radius) else float("nan")
    attrs[6] = float(has_diameter)
    attrs[7] = float(has_radius)
    attrs[8] = float(math.isfinite(dvalue))
    attrs[9] = dvalue / scale if math.isfinite(dvalue) else 0.0
    attrs[10] = float(math.isfinite(rvalue))
    attrs[11] = rvalue / scale if math.isfinite(rvalue) else 0.0
    attrs[12] = float(entity_type in {"CIRCLE", "ARC"})
    closed = getattr(data["geometry"], "is_closed", [])
    attrs[13] = float(bool(closed[geometry_index])) if geometry_index < len(closed) else 0.0

    geom_span = max(geom_width, geom_height)
    if math.isfinite(dvalue) and geom_span > 1e-9:
        attrs[14] = abs(dvalue / scale - geom_span) / max(dvalue / scale, geom_span, 1e-9)
    if math.isfinite(rvalue) and geom_span > 1e-9:
        attrs[15] = abs(2.0 * rvalue / scale - geom_span) / max(2.0 * rvalue / scale, geom_span, 1e-9)

    for offset, name in enumerate(geom_type_names, start=16):
        attrs[offset] = float(geometry_type == name)
    for offset, name in zip((24, 25, 26), ("CIRCLE", "ARC", "ELLIPSE")):
        attrs[offset] = float(entity_type == name)
    aspect = min(geom_width, geom_height) / max(geom_width, geom_height, 1e-9)
    attrs[27] = aspect
    attrs[28] = geom_span
    attrs[29] = aspect  # bbox-only proxy; no area-derived circularity
    attrs[38] = 1.0  # diagnostic override marker, masked from the model
    return attrs


def attach_text_geometry_labels(data, labels):
    """Attach reviewed correspondences without manufacturing negative labels.

    Positive reviewed pairs omitted by spatial candidate generation are added
    as scoring candidates. Such synthetic edges are excluded from GNN message
    passing so the ground-truth edge itself cannot leak into its prediction.
    """
    handles_text = [str(v).strip() for v in data["text"].source_handle]
    handles_geometry = [str(v).strip() for v in data["geometry"].source_handle]
    text_index_by_handle = {handle: i for i, handle in enumerate(handles_text)}
    geometry_index_by_handle = {handle: i for i, handle in enumerate(handles_geometry)}
    supported = {
        "dimension_value_candidate", "part_label_candidate",
        "geometry_description_candidate", "gdt_candidate",
        "reviewed_match_candidate",
    }
    counts = {
        "positive": 0, "negative": 0, "unlabeled": 0,
        "positive_edges_added": 0, "orphan_text_handles": 0,
        "orphan_geometry_handles": 0,
    }

    # Snapshot existing candidate pairs before appending any missing reviewed positives.
    existing = {}
    for edge_type in list(data.edge_types):
        if edge_type[0] != "text" or edge_type[2] != "geometry" or edge_type[1] not in supported:
            continue
        store = data[edge_type]
        edge_index = store.edge_index
        existing[edge_type] = {
            (int(edge_index[0, i]), int(edge_index[1, i]))
            for i in range(edge_index.size(1))
        }

    # A reviewed positive is authoritative: ensure it has a candidate edge,
    # even if the spatial top-k / distance filter did not produce one.
    for (text_handle, geometry_handle, relation), label in labels.items():
        if int(label) != 1:
            continue
        ti = text_index_by_handle.get(str(text_handle).strip())
        gi = geometry_index_by_handle.get(str(geometry_handle).strip())
        if ti is None:
            counts["orphan_text_handles"] += 1
            continue
        if gi is None:
            counts["orphan_geometry_handles"] += 1
            continue
        selected_relations = _text_geometry_relations_for_label(data, ti, relation)
        for selected_relation in selected_relations:
            edge_type = ("text", selected_relation, "geometry")
            if edge_type not in data.edge_types:
                # Canonical schema normally creates this store; keep robust for
                # externally produced graphs too.
                data[edge_type].edge_index = torch.empty((2, 0), dtype=torch.long)
                data[edge_type].edge_attr = torch.empty((0, 39), dtype=torch.float)
            if (ti, gi) not in existing.setdefault(edge_type, set()):
                store = data[edge_type]
                new_index = torch.tensor([[ti], [gi]], dtype=torch.long, device=store.edge_index.device)
                new_attr = torch.tensor(
                    [_reviewed_edge_features(data, ti, gi)],
                    dtype=store.edge_attr.dtype if store.edge_attr.numel() else torch.float,
                    device=store.edge_attr.device,
                )
                store.edge_index = torch.cat([store.edge_index, new_index], dim=1)
                store.edge_attr = torch.cat([store.edge_attr, new_attr], dim=0)
                # Existing edges pass messages; synthetic reviewed candidates do not.
                old_mask = getattr(store, "message_passing_mask", None)
                if old_mask is None:
                    old_mask = torch.ones(
                        store.edge_index.size(1) - 1,
                        dtype=torch.bool,
                        device=store.edge_index.device,
                    )
                store.message_passing_mask = torch.cat([
                    old_mask,
                    torch.tensor([False], dtype=torch.bool, device=store.edge_index.device),
                ])
                existing[edge_type].add((ti, gi))
                counts["positive_edges_added"] += 1

    # Attach labels by exact handle pair and relation. Unreviewed candidates
    # remain masked, not negative.
    for edge_type in list(data.edge_types):
        if edge_type[0] != "text" or edge_type[2] != "geometry" or edge_type[1] not in supported:
            continue
        store = data[edge_type]
        edge_index = store.edge_index
        targets, mask = [], []
        for edge_i in range(edge_index.size(1)):
            text_index = int(edge_index[0, edge_i])
            geometry_index = int(edge_index[1, edge_i])
            text_handle = handles_text[text_index]
            geometry_handle = handles_geometry[geometry_index]
            label = labels.get(
                (text_handle, geometry_handle, edge_type[1]),
                labels.get((text_handle, geometry_handle, "*")),
            )
            if label is None:
                targets.append(0)
                mask.append(False)
                counts["unlabeled"] += 1
            else:
                targets.append(int(label))
                mask.append(True)
                counts["positive" if int(label) else "negative"] += 1
        store.match_y = torch.tensor(targets, dtype=torch.float, device=edge_index.device)
        store.match_mask = torch.tensor(mask, dtype=torch.bool, device=edge_index.device)
        if getattr(store, "message_passing_mask", None) is None:
            store.message_passing_mask = torch.ones(
                edge_index.size(1), dtype=torch.bool, device=edge_index.device
            )

    data.graph_metadata["text_geometry_supervision"] = {
        "provenance": "reviewed_text_geometry_correspondence_labels",
        "counts": counts,
        "negative_policy": "only_explicit_negative_labels_are_negative;_unlabeled_pairs_are_unlabeled",
        "positive_only_objective": "per_text_listwise_positive_ranking",
    }
    return data


def attach_geometry_targets(data, targets: dict[str, dict[str, float]]):
    """Attach log1p regression targets with independent per-task masks."""
    handles = data["geometry"].source_handle
    closed = getattr(data["geometry"], "is_closed", torch.zeros(len(handles), dtype=torch.bool))
    raw_area = getattr(data["geometry"], "raw_geometry_area", [0.0] * len(handles))
    raw_perimeter = getattr(data["geometry"], "raw_geometry_perimeter", [0.0] * len(handles))
    entity_types = [
        str(value).upper()
        for value in getattr(data["geometry"], "entity_type", ["OTHER"] * len(handles))
    ]
    for name in ("length", "area", "radius"):
        values = [0.0] * len(handles)
        mask = [False] * len(handles)
        for index, handle in enumerate(handles):
            raw_value = targets.get(str(handle), {}).get(name)
            try:
                value = float(raw_value)
            except (TypeError, ValueError, OverflowError):
                continue
            if not math.isfinite(value) or value < 0.0:
                continue
            # Task-specific semantic validity prevents meaningless zero targets.
            if name == "area" and (
                not bool(closed[index])
                or not (
                    entity_types[index] == "CIRCLE"
                    or (
                        index < len(raw_area) and float(raw_area[index]) > 0.0
                        and index < len(raw_perimeter) and float(raw_perimeter[index]) > 0.0
                    )
                )
            ):
                continue
            if name == "radius" and entity_types[index] not in {"CIRCLE", "ARC"}:
                continue
            values[index] = math.log1p(value)
            mask[index] = True
        data["geometry"][f"{name}_y"] = torch.tensor(values, dtype=torch.float)
        data["geometry"][f"{name}_mask"] = torch.tensor(mask, dtype=torch.bool)
    data.graph_metadata["target_encoding"] = "log1p"
    data.graph_metadata["target_validity"] = {
        "area": "closed CIRCLE uses pi*predicted_radius^2; other closed shapes require raw area/perimeter and use corrected-length scale",
        "radius": "entity_type in {CIRCLE, ARC}",
        "length": "finite reviewed target; CIRCLE/ARC length is supervised as a derived metric, not a direct regression target",
    }
    data.graph_metadata["target_provenance"] = "reviewed_external_ground_truth"
    return data


def load_class_mapping(path: str | Path) -> dict[str, int]:
    """Load class names and IDs from classes.json."""
    path = Path(path)
    class_to_id = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(class_to_id, dict):
        raise ValueError("classes.json must contain a JSON object.")
    class_to_id = {
        str(name).strip(): int(class_id)
        for name, class_id in class_to_id.items()
    }
    if len(set(class_to_id.values())) != len(class_to_id):
        raise ValueError("Duplicate class IDs found in classes.json.")
    return class_to_id


def build_training_file_old(
    graph_path: str | Path,
    labels_path: str | Path,
    classes_path: str | Path | None,
    output_path: str | Path,
):
    """Attach classification and independent length/area/radius ground truth."""
    graph_path = Path(graph_path)
    output_path = Path(output_path)
    if not graph_path.exists():
        raise FileNotFoundError(f"Graph file not found: {graph_path}")

    data = torch.load(graph_path, map_location="cpu", weights_only=False)
    if (data.graph_metadata.get("feature_version") != 8
            or data.graph_metadata.get("measurement_derivation_schema") != "circle_arc_length_from_predicted_radius_v1"):
        raise ValueError(
            "Rebuild the semantic graph with circle/arc deterministic-length metadata."
        )
    sweep_angles = getattr(data["geometry"], "arc_sweep_angle_rad", None)
    if sweep_angles is None or len(sweep_angles) != data["geometry"].x.size(0):
        raise ValueError("Graph is missing per-geometry arc sweep angles; rebuild it.")
    if (
        data.graph_metadata.get("geometry_feature_schema") != "dxf_geometry_shape_v8"
        or data.graph_metadata.get("geometry_feature_names") != list(GEOMETRY_FEATURE_NAMES)
        or data.graph_metadata.get("geometry_feature_dimension") != 24 + len(GEOMETRY_FEATURE_NAMES)
        or data["geometry"].x.size(-1) != 24 + len(GEOMETRY_FEATURE_NAMES)
        or data["text"].x.size(-1) != len(TEXT_FEATURE_NAMES)
        or data.graph_metadata.get("text_feature_schema") != list(TEXT_FEATURE_NAMES)
    ):
        raise ValueError("Graph geometry/text feature schema/order is invalid; rebuild the v8 graph.")

    handle_labels = load_handle_labels(labels_path)
    class_to_id = load_class_mapping(classes_path) if classes_path else {}
    if class_to_id:
        data = attach_labels(data, handle_labels, class_to_id)
    else:
        count = len(data["geometry"].source_handle)
        data["geometry"].y = torch.full((count,), -100, dtype=torch.long)
        data["geometry"].class_mask = torch.zeros(count, dtype=torch.bool)
        data["geometry"].train_mask = data["geometry"].class_mask.clone()

    targets = load_geometry_targets(labels_path)
    data = attach_geometry_targets(data, targets)
    data = attach_text_geometry_labels(data, load_text_geometry_labels(labels_path))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(data, output_path)

    print("=" * 60)
    print("Labeled semantic graph created")
    print(f"Graph            : {graph_path}")
    print(f"Labels           : {labels_path}")
    print(f"Output           : {output_path}")
    print(f"Geometry nodes   : {len(data['geometry'].source_handle)}")
    print(f"Class labels     : {int(data['geometry'].class_mask.sum())}")
    for name in ("length", "area", "radius"):
        print(f"{name.title():16s}: {int(data['geometry'][name + '_mask'].sum())}")
    print(f"Text link labels : {data.graph_metadata.get('text_geometry_supervision', {}).get('counts', {})}")
    print("=" * 60)
    return data


def build_training_file(
    graph_path: str | Path,
    labels_path: str | Path,
    text_labels_path: str | Path | None,
    classes_path: str | Path | None,
    output_path: str | Path,
):
    """Attach geometry labels, regression targets and text-geometry labels."""

    graph_path = Path(graph_path)
    labels_path = Path(labels_path)
    output_path = Path(output_path)

    if text_labels_path is not None:
        text_labels_path = Path(text_labels_path)
    else:
        # Backward compatibility
        text_labels_path = labels_path

    if not graph_path.exists():
        raise FileNotFoundError(f"Graph file not found: {graph_path}")

    if not labels_path.exists():
        raise FileNotFoundError(f"Geometry labels not found: {labels_path}")

    if not text_labels_path.exists():
        raise FileNotFoundError(
            f"Text geometry labels not found: {text_labels_path}"
        )

    data = torch.load(
        graph_path,
        map_location="cpu",
        weights_only=False,
    )

    if (data.graph_metadata.get("feature_version") != 8
            or data.graph_metadata.get("measurement_derivation_schema") != "circle_arc_length_from_predicted_radius_v1"):
        raise ValueError(
            "Rebuild the semantic graph with circle/arc deterministic-length metadata."
        )
    sweep_angles = getattr(data["geometry"], "arc_sweep_angle_rad", None)
    if sweep_angles is None or len(sweep_angles) != data["geometry"].x.size(0):
        raise ValueError("Graph is missing per-geometry arc sweep angles; rebuild it.")

    if (
        data.graph_metadata.get("geometry_feature_schema") != "dxf_geometry_shape_v8"
        or data.graph_metadata.get("geometry_feature_names") != list(GEOMETRY_FEATURE_NAMES)
        or data.graph_metadata.get("geometry_feature_dimension") != 24 + len(GEOMETRY_FEATURE_NAMES)
        or data["geometry"].x.size(-1) != 24 + len(GEOMETRY_FEATURE_NAMES)
        or data["text"].x.size(-1) != len(TEXT_FEATURE_NAMES)
        or data.graph_metadata.get("text_feature_schema") != list(TEXT_FEATURE_NAMES)
    ):
        raise ValueError(
            "Graph geometry/text feature schema/order is invalid; "
            "rebuild the v8 graph."
        )

    # -------------------------------------------------
    # 1. Geometry classification labels
    # -------------------------------------------------

    handle_labels = load_handle_labels(labels_path)
    class_to_id = (
        load_class_mapping(classes_path)
        if classes_path else {}
    )
    if class_to_id:
        data = attach_labels(
            data,
            handle_labels,
            class_to_id,
        )
    else:
        count = len(data["geometry"].source_handle)
        data["geometry"].y = torch.full((count,), -100, dtype=torch.long)
        data["geometry"].class_mask = torch.zeros(count, dtype=torch.bool)
        data["geometry"].train_mask = (data["geometry"].class_mask.clone())

    # -------------------------------------------------
    # 2. Geometry regression targets
    # -------------------------------------------------

    targets = load_geometry_targets(labels_path)
    data = attach_geometry_targets(data, targets)

    # -------------------------------------------------
    # 3. Text-to-Geometry correspondence labels
    # -------------------------------------------------

    text_labels = load_text_geometry_labels(text_labels_path)
    data = attach_text_geometry_labels(data, text_labels)

    # -------------------------------------------------
    # 4. Save
    # -------------------------------------------------

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    torch.save(data, output_path)

    # -------------------------------------------------
    # 5. Diagnostics
    # -------------------------------------------------

    print("=" * 60)
    print("Labeled semantic graph created")
    print(f"Graph              : {graph_path}")
    print(f"Geometry labels    : {labels_path}")
    print(f"Text labels        : {text_labels_path}")
    print(f"Output             : {output_path}")
    print(f"Geometry nodes     : {len(data['geometry'].source_handle)}")
    print(f"Text nodes         : {len(data['text'].source_handle)}")
    print(f"Class labels       : {int(data['geometry'].class_mask.sum())}")
    for name in ("length", "area", "radius"):
        print(
            f"{name.title():18s}: "
            f"{int(data['geometry'][name + '_mask'].sum())}"
        )
    print(
        "Text link labels   :",
        data.graph_metadata.get(
            "text_geometry_supervision", {}
        ).get("counts", {})
    )
    print("=" * 60)
    return data


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Attach reviewed labels to a semantic graph.")
    parser.add_argument("--graph", required=True)
    parser.add_argument("--labels", required=True, help="CSV/JSON with source_handle,label,length,area,radius")
    parser.add_argument("--text-labels", default=None, help="CSV/JSON with text_handle,geometry_handle,relation_type,is_match")
    parser.add_argument("--classes", default=None, help="Optional class-to-ID JSON mapping")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    build_training_file(args.graph, args.labels, args.text_labels, args.classes, args.output)
