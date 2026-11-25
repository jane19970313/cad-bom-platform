import math

from shapely.geometry import Polygon, Point

from app.services.dxf_engine.ai_gnn.geometry_features import (
    GEOMETRY_FEATURE_NAMES,
    extract_geometry_descriptors,
)


def _element(geometry, entity_type="LWPOLYLINE", closed=True):
    return {
        "geometry_2d": geometry,
        "geometry_type": "CLOSED_PROFILE" if closed else "LINEAR_GEOMETRY",
        "is_closed": closed,
        "source": {"entity_type": entity_type},
    }


def test_v7_descriptor_schema_is_fixed_finite_and_has_no_area_leakage():
    polygon = Point(0, 0).buffer(20, resolution=24)
    values = extract_geometry_descriptors(_element(polygon, "CIRCLE"), scale=2.0)
    assert len(GEOMETRY_FEATURE_NAMES) == 21
    assert len(values) == len(GEOMETRY_FEATURE_NAMES)
    assert all(math.isfinite(value) for value in values)
    forbidden = {"area", "area_over_scale_squared", "bbox_fill_ratio", "solidity", "circularity"}
    assert not forbidden.intersection(GEOMETRY_FEATURE_NAMES)
    assert values[17] == 1.0  # circle indicator
    assert values[18] == 0.0  # not an ARC
    assert values[19] == 1.0  # perimeter is available


def test_hole_topology_is_extracted_without_exposing_hole_area():
    outer = [(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)]
    inner = [(30, 30), (70, 30), (70, 70), (30, 70), (30, 30)]
    polygon = Polygon(outer, [inner])
    values = extract_geometry_descriptors(_element(polygon), scale=1.0)
    by_name = dict(zip(GEOMETRY_FEATURE_NAMES, values))
    assert by_name["hole_count_log"] > 0.0
    assert by_name["hole_perimeter_log_over_scale"] > 0.0
    assert by_name["hole_boundary_fraction"] > 0.0
    assert by_name["has_hole_data"] == 1.0
    assert not any("area" in name for name in GEOMETRY_FEATURE_NAMES)


def test_length_descriptors_obey_linear_scale_normalization():
    polygon = Point(0, 0).buffer(10, resolution=16)
    one = extract_geometry_descriptors(_element(polygon, "CIRCLE"), scale=1.0)
    two = extract_geometry_descriptors(_element(polygon, "CIRCLE"), scale=2.0)
    names = dict(zip(GEOMETRY_FEATURE_NAMES, range(len(GEOMETRY_FEATURE_NAMES))))
    for name in (
        "bbox_diagonal_over_scale",
        "segment_length_mean_over_scale",
        "segment_length_max_over_scale",
        "principal_axis_major_over_scale",
        "principal_axis_minor_over_scale",
    ):
        index = names[name]
        assert math.isclose(two[index], one[index] / 2.0, rel_tol=1e-6, abs_tol=1e-8)


def test_open_geometry_marks_hole_information_unavailable():
    from shapely.geometry import LineString
    line = LineString([(0, 0), (10, 0), (10, 5)])
    values = extract_geometry_descriptors(_element(line, closed=False), scale=1.0)
    by_name = dict(zip(GEOMETRY_FEATURE_NAMES, values))
    assert by_name["has_perimeter"] == 1.0
    assert by_name["has_hole_data"] == 0.0
    assert by_name["hole_count_log"] == 0.0


def test_arc_entity_exposes_arc_length_but_not_circle_flag():
    from shapely.geometry import LineString
    arc_like = LineString([(10, 0), (7, 7), (0, 10)])
    values = extract_geometry_descriptors(_element(arc_like, "ARC", closed=False), scale=2.0)
    by_name = dict(zip(GEOMETRY_FEATURE_NAMES, values))
    assert by_name["arc_length_log_over_scale"] > 0.0
    assert by_name["is_arc"] == 1.0
    assert by_name["is_circle"] == 0.0
