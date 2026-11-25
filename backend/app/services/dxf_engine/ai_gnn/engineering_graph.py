from __future__ import annotations

import networkx as nx

from app.services.dxf_engine.models.engineering import (
    Classification,
    EngineeringElement,
)


ENGINEERING_TYPES = {"BEAM", "COLUMN", "PLATE", "BOLT", "CONNECTION", "OTHER"}


def build_engineering_graph(predictions, geometry_elements, semantic_graph=None):
    """Convert geometry-node predictions into traceable engineering elements.

    This is the first Layer-3 adapter: one predicted engineering object per
    geometry node. Spatial edges are emitted as candidate relationships, not
    asserted physical connections. Grouping several CAD entities into one
    fabricated member and predicting true connection types require separately
    labeled relation/assembly training and are intentionally not guessed here.
    """
    geometry_by_handle = {
        str(getattr(item, "source_handle", "")): item
        for item in geometry_elements
    }
    graph = nx.MultiGraph()
    element_by_handle = {}

    for prediction in predictions:
        handle = str(prediction["source_handle"])
        geometry = geometry_by_handle.get(handle)
        if geometry is None:
            continue
        predicted_type = str(prediction["predicted_type"]).upper()
        if predicted_type not in ENGINEERING_TYPES:
            predicted_type = "OTHER"
        confidence = float(prediction.get("confidence", 0.0))
        engineering_element = EngineeringElement(
            element_id=str(prediction.get("element_id") or geometry.element_id),
            classification=Classification(
                category="STRUCTURAL_OBJECT",
                engineering_type=predicted_type,
                confidence=confidence,
                status="gnn_predicted",
                evidence=["heterogeneous_gnn_geometry_classification"],
            ),
            source_handles=[handle],
            properties={
                "geometry_type": geometry.geometry_type,
                "caption": geometry.caption,
                # Keep deterministic measurements and GNN estimates separate;
                # fusion is a downstream, explicitly validated operation.
                "analytic_length": geometry.length,
                "analytic_area": geometry.area,
                "analytic_radius": getattr(geometry, "radius_measured", None),
                "raw_dxf_radius": geometry.radius,
                "predicted_length": prediction.get("predicted_length"),
                "predicted_area": prediction.get("predicted_area"),
                "predicted_area_source": prediction.get("predicted_area_source"),
                "predicted_radius": prediction.get("predicted_radius"),
                "direct_measurements": prediction.get("direct_measurements"),
                "relation_measurements": prediction.get("relation_measurements"),
                "fusion_weights": prediction.get("fusion_weights"),
                "measurement_validity": prediction.get("measurement_validity"),
                "length": geometry.length,
                "area": geometry.area,
                "is_closed": geometry.is_closed,
                "is_valid": geometry.is_valid,
            },
        )
        element_by_handle[handle] = engineering_element
        graph.add_node(
            engineering_element.element_id,
            engineering_element=engineering_element,
            source_handle=handle,
            engineering_type=predicted_type,
            confidence=confidence,
        )

    # Preserve graph-derived adjacency as candidates, never as confirmed
    # structural connections.
    if semantic_graph is not None and ("geometry", "near", "geometry") in semantic_graph.edge_types:
        edge_index = semantic_graph[("geometry", "near", "geometry")].edge_index
        handles = semantic_graph["geometry"].source_handle
        edge_attr = semantic_graph[("geometry", "near", "geometry")].edge_attr
        for edge_i in range(edge_index.size(1)):
            src_idx = int(edge_index[0, edge_i])
            dst_idx = int(edge_index[1, edge_i])
            src_handle = str(handles[src_idx])
            dst_handle = str(handles[dst_idx])
            src_element = element_by_handle.get(src_handle)
            dst_element = element_by_handle.get(dst_handle)
            if src_element is None or dst_element is None:
                continue
            distance = float(edge_attr[edge_i, 0])
            proximity = float(edge_attr[edge_i, 1])
            graph.add_edge(
                src_element.element_id,
                dst_element.element_id,
                relationship="spatial_candidate",
                distance_normalized=distance,
                confidence=proximity,
                status="candidate_not_validated_connection",
            )

    return graph
