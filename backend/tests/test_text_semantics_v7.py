import math
import torch

from shapely.geometry import LineString, Point

from app.services.dxf_engine.ai_gnn.graph_builder import (
    _anchor_specs,
    _collinear_score,
    build_semantic_graph,
)
from app.services.dxf_engine.ai_gnn.labels import attach_text_geometry_labels
from torch_geometric.data import HeteroData

from app.services.dxf_engine.ai_gnn.text_semantics import (
    classify_text,
    load_text_config,
    normalize_text,
    parse_measurement_evidence,
    tokenize_text,
)


def _geometry(handle, entity_type, geometry, center=None, radius=None):
    return {
        "element_id": handle,
        "source_handle": handle,
        "source": {"entity_handle": handle, "entity_type": entity_type, "layer": "0"},
        "geometry_2d": geometry,
        "geometry_type": "CLOSED_PROFILE" if entity_type == "CIRCLE" else "LINEAR_GEOMETRY",
        "center": center,
        "is_closed": entity_type == "CIRCLE",
        "is_valid": True,
        "radius": radius,
        "radius_measured": radius,
        "length": float(geometry.length),
        "area": float(geometry.area),
    }


def _text(handle, content, xy):
    return {
        "element_id": handle,
        "source_handle": handle,
        "source": {"entity_handle": handle, "entity_type": "TEXT", "layer": "TEXT"},
        "text": content,
        "position": Point(xy),
        "position_moved": None,
        "bound": None,
        "bound_moved": None,
        "angle": 0.0,
    }


def test_configurable_cad_symbols_and_part_tokens():
    config = load_text_config()
    custom = {"replacements": [{"pattern": r"^\?([0-9]+)$", "replacement": "I$1", "enabled": True}]}
    assert normalize_text("?10", custom) == "I10"
    assert normalize_text("?10", config) == "?10"
    diameter = parse_measurement_evidence("%%C6500", config)
    assert diameter["has_diameter_symbol"]
    assert diameter["diameter_value"] == 6500.0
    radius = parse_measurement_evidence("R25", config)
    assert radius["has_radius_symbol"]
    assert radius["radius_value"] == 25.0

    assert classify_text("H294X200", config)[0] == "PART_LABEL"
    assert classify_text("SJ-R-12000", config)[0] == "PART_LABEL"
    assert classify_text("1#??", config)[0] == "PART_LABEL"
    assert classify_text("BRACKET A", config)[0] == "PART_LABEL"
    assert classify_text("均布荷载 2.5kN/m", config)[0] == "ANNOTATION"


def test_chinese_tokenization_is_nonempty_without_mandatory_jieba():
    config = load_text_config()
    tokens = tokenize_text("钢板厚度10mm", config)
    assert tokens
    assert any("钢" in token or "板" in token for token in tokens)


def test_collinear_tolerance_is_independent_and_configurable():
    a = LineString([(0, 0), (100, 0)])
    b = LineString([(0, 5), (100, 5)])
    direction = (1.0, 0.0)
    assert _collinear_score(a, b, direction, direction, tolerance=10.0) > 0.0
    assert _collinear_score(a, b, direction, direction, tolerance=2.0) == 0.0


def test_anchor_features_include_local_tangent_and_curvature():
    element = _geometry(
        "P1", "LWPOLYLINE",
        LineString([(0, 0), (10, 0), (10, 10)]),
    )
    anchors = _anchor_specs(element)
    vertex = next(row for row in anchors if row[1] == "VERTEX")
    assert math.hypot(*vertex[2]) > 0.9
    assert abs(vertex[3]) > 0.01


def test_annotation_is_preserved_but_never_connected_to_geometry():
    circle = _geometry("C1", "CIRCLE", Point(0, 0).buffer(10), Point(0, 0), 10.0)
    texts = [
        _text("T1", "%%C20", (0, 12)),
        _text("T2", "均布荷载 2.5kN/m", (0, 14)),
    ]
    dimension = {
        "element_id": "D1",
        "source_handle": "D1",
        "source": {"entity_handle": "D1", "entity_type": "DIMENSION", "layer": "DIM"},
        "dimension_type": "DIAMETRIC",
        "endpoints": [(0, 0), (10, 0)],
        "definition_points": [(0, 0), (10, 0)],
        "center": Point(0, 0),
        "measurement_point": Point(10, 0),
        "length": 20.0,
        "actual_length": 20.0,
    }
    graph = build_semantic_graph(
        [circle], [dimension], texts,
        scale=1.0, spatial_tolerance=50.0, dimension_tolerance=100.0,
        text_tolerance=50.0, collinear_tolerance=3.0,
    )
    assert graph.graph_metadata["feature_version"] == 7
    assert graph["text"].semantic_type == ["DIMENSION_VALUE", "ANNOTATION"]
    assert graph["text"].has_diameter_symbol == [True, False]
    edge_type = ("text", "dimension_value_candidate", "geometry")
    edge_index = graph[edge_type].edge_index
    assert edge_index.size(1) == 1
    assert graph[edge_type].edge_attr.shape[1] == 38
    assert abs(float(graph[edge_type].edge_attr[0, 14])) < 1e-4
    assert int(edge_index[0, 0]) == 0
    assert int(edge_index[1, 0]) == 0
    # Annotation text remains a node but has no dimension or geometry links.
    for relation in (
        "dimension_value_candidate", "part_label_candidate",
        "geometry_description_candidate", "gdt_candidate",
    ):
        edges = graph[("text", relation, "geometry")].edge_index
        assert not bool((edges[0] == 1).any())
    assert graph[("text", "labels", "dimension")].edge_index.size(1) >= 1



def test_reviewed_text_geometry_labels_mask_unreviewed_candidates():
    graph = HeteroData()
    graph["text"].source_handle = ["T1", "T2"]
    graph["geometry"].source_handle = ["G1", "G2"]
    edge_type = ("text", "dimension_value_candidate", "geometry")
    graph[edge_type].edge_index = torch.tensor([[0, 1], [0, 1]], dtype=torch.long)
    graph[edge_type].edge_attr = torch.zeros((2, 38))
    graph.graph_metadata = {}
    attach_text_geometry_labels(
        graph,
        {("T1", "G1", "dimension_value_candidate"): 1},
    )
    assert graph[edge_type].match_y.tolist() == [1.0, 0.0]
    assert graph[edge_type].match_mask.tolist() == [True, False]
    assert graph.graph_metadata["text_geometry_supervision"]["counts"]["positive"] == 1



def test_mirror_candidates_support_diagonal_axes():
    from shapely.geometry import box

    geometry_a = _geometry("A", "LWPOLYLINE", box(9.5, -0.5, 10.5, 0.5))
    geometry_b = _geometry("B", "LWPOLYLINE", box(-0.5, 9.5, 0.5, 10.5))
    graph = build_semantic_graph(
        [geometry_a, geometry_b], [], [],
        spatial_tolerance=100.0, collinear_tolerance=1.0,
        mirror_tolerance=0.1,
    )
    edge_type = ("geometry", "mirror_candidate", "geometry")
    edge_index = graph[edge_type].edge_index
    assert edge_index.size(1) == 1
    # Reflection axis y=x is 45 degrees, represented as 45/180 == 0.25.
    assert abs(float(graph[edge_type].edge_attr[0, 1]) - 0.25) < 1e-6
