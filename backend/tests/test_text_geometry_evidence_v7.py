import math

from shapely.geometry import LineString, Point

from app.services.dxf_engine.ai_gnn.graph_builder import (
    _collinear_score,
    build_semantic_graph,
)
from app.services.dxf_engine.ai_gnn.text_semantics import (
    classify_text,
    load_text_config,
    normalize_text,
    parse_measurement_evidence,
    tokenize_text,
)


def test_configurable_cad_text_patterns_and_symbols():
    config = load_text_config()
    assert classify_text("H294X200", config)[0] == "PART_LABEL"
    assert classify_text("1#??", config)[0] == "PART_LABEL"
    assert classify_text("SJ-R-12000", config)[0] == "PART_LABEL"
    assert classify_text("?10", config)[0] == "PART_LABEL"
    assert classify_text("%%C6500", config)[0] == "DIMENSION_VALUE"

    normalized = normalize_text("%%C50 %%D90 %%P0.1", config)
    assert normalized == "Ø50 °90 ±0.1"
    evidence = parse_measurement_evidence("%%C50", config)
    assert evidence["has_diameter_symbol"]
    assert evidence["diameter_value"] == 50.0


def test_chinese_tokenization_has_dependency_free_fallback():
    tokens = tokenize_text(
        "均布荷载安装要求",
        {"chinese_tokenization": {"use_jieba": False, "minimum_word_length": 1}},
    )
    assert tokens
    assert "均布" in tokens
    assert "布荷" in tokens


def test_annotation_is_retained_but_never_links_to_geometry_or_dimension():
    circle = Point(0, 0).buffer(25, resolution=32)
    geometry = {
        "element_id": "G1",
        "source_handle": "G1",
        "source": {"entity_handle": "G1", "entity_type": "CIRCLE", "layer": "0"},
        "geometry_2d": circle,
        "geometry_type": "CLOSED_PROFILE",
        "center": (0, 0),
        "is_closed": True,
        "is_valid": True,
        "radius": 25.0,
        "radius_measured": 25.0,
        "length": circle.length,
        "area": circle.area,
    }
    dimension = {
        "element_id": "D1",
        "source_handle": "D1",
        "source": {"entity_handle": "D1", "entity_type": "DIMENSION", "layer": "DIM"},
        "dimension_type": "DIAMETRIC",
        "endpoints": [(0, 0), (25, 0)],
        "definition_points": [],
        "center": (0, 0),
        "measurement_point": (25, 0),
        "length": 50.0,
        "actual_length": None,
    }
    texts = [
        {
            "element_id": "T1",
            "source_handle": "T1",
            "source": {"entity_handle": "T1", "entity_type": "TEXT", "layer": "DIM"},
            "text": "%%C50",
            "position": (30, 0),
            "bound": Point(30, 0),
            "angle": 0.0,
        },
        {
            "element_id": "T2",
            "source_handle": "T2",
            "source": {"entity_handle": "T2", "entity_type": "MTEXT", "layer": "NOTE"},
            "text": "NOTE: 均布荷载 Ø50 2.5kN/m",
            "position": (5, 5),
            "bound": Point(5, 5),
            "angle": 0.0,
        },
    ]

    graph = build_semantic_graph(
        geometry_elements=[geometry],
        dimension_elements=[dimension],
        text_elements=texts,
        scale=1.0,
        spatial_tolerance=100.0,
        dimension_tolerance=100.0,
        text_tolerance=100.0,
    )

    assert graph.graph_metadata["feature_version"] == 7
    assert graph["text"].semantic_type == ["DIMENSION_VALUE", "ANNOTATION"]

    relation = ("text", "dimension_value_candidate", "geometry")
    assert graph[relation].edge_index.size(1) == 1
    assert graph[relation].edge_attr.shape == (1, 38)

    attrs = graph[relation].edge_attr[0]
    # Feature indices 30-37 carry linked dimension evidence.
    assert attrs[30].item() == 1.0  # linked DIAMETRIC dimension
    assert attrs[32].item() == 1.0  # linked dimension value is valid
    assert math.isclose(attrs[33].item(), 50.0, rel_tol=1e-6)
    assert math.isclose(attrs[34].item(), 1.0, rel_tol=1e-5)
    assert attrs[36].item() == 1.0  # linked dimension exists
    assert attrs[37].item() == 1.0  # dimension kind matches diameter symbol

    # General notes remain represented as nodes but have no outgoing
    # text-to-geometry or text-to-dimension evidence edges.
    assert graph["text"].x.size(0) == 2
    for edge_type in graph.edge_types:
        if edge_type[0] == "text":
            edge_index = graph[edge_type].edge_index
            assert not bool((edge_index[0] == 1).any())


def test_collinear_tolerance_is_independent_and_curvature_is_not_assumed():
    first = LineString([(0, 0), (100, 0)])
    second = LineString([(0, 5), (100, 5)])
    direction = (1.0, 0.0)
    assert math.isclose(
        _collinear_score(first, second, direction, direction, 10.0),
        0.5,
        rel_tol=1e-6,
    )
    assert _collinear_score(
        first, second, direction, direction, 2.0
    ) == 0.0

    # A bent polyline has no single representative direction, so it must not
    # be forced into a straight-line collinearity score. Its local tangent and
    # curvature evidence is represented by geometry anchors/edge attributes.
    bent = LineString([(0, 0), (50, 0), (50, 50)])
    assert _collinear_score(
        bent, second, None, direction, 10.0
    ) == 0.0


def test_curvature_and_tangent_are_geometry_relation_evidence():
    first = Point(0, 0).buffer(25, resolution=32)
    second = Point(60, 0).buffer(25, resolution=32)
    elements = []
    for handle, geom in (("C1", first), ("C2", second)):
        elements.append({
            "element_id": handle,
            "source_handle": handle,
            "source": {"entity_handle": handle, "entity_type": "CIRCLE", "layer": "0"},
            "geometry_2d": geom,
            "geometry_type": "CLOSED_PROFILE",
            "center": (geom.centroid.x, geom.centroid.y),
            "is_closed": True,
            "is_valid": True,
            "radius": 25.0,
        })
    graph = build_semantic_graph(
        geometry_elements=elements,
        dimension_elements=[],
        text_elements=[],
        spatial_tolerance=100.0,
    )
    edge_type = ("geometry", "near", "geometry")
    edge_index = graph[edge_type].edge_index
    edge_attr = graph[edge_type].edge_attr
    assert edge_index.size(1) == 1
    # Geometry relation features 7 and 8 are tangent continuity and
    # curvature similarity respectively.
    assert edge_attr[0, 7].item() > 0.8
    assert edge_attr[0, 8].item() > 0.9
