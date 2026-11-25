from __future__ import annotations

import hashlib
import math
import re
from collections import defaultdict
from typing import Any

from shapely.geometry import Point, LineString
from shapely.ops import nearest_points
from shapely.strtree import STRtree

from .geometry_features import GEOMETRY_FEATURE_NAMES, extract_geometry_descriptors

from .text_semantics import (
    classify_text_categories, load_text_config, normalize_text,
    parse_measurement_evidence, tokenize_text,
)


# GeometryElement.geometry_type is assigned by geometry/entity_converter.py.
# Keep eight one-hot slots; the 24th feature is the permitted radius descriptor,
# but use the actual classifier vocabulary so known shapes are not all-zero.
TEXT_CATEGORIES = ("ANNOTATION", "TOLERANCE_GDT", "DIMENSION_VALUE", "PART_LABEL", "GEOMETRY_DESCRIPTION", "UNKNOWN")
TEXT_FEATURE_NAMES = (
    "normalized_x", "normalized_y", "bbox_width", "bbox_height", "angle",
    "text_length_log", "digit_count_log", "has_diameter_symbol",
    "has_radius_symbol",
    *tuple(f"category_{category.lower()}" for category in TEXT_CATEGORIES),
    *tuple(f"lexical_hash_{index}" for index in range(32)),
)

GEOMETRY_TYPES = (
    "CLOSED_PROFILE", "LINEAR_GEOMETRY", "POINT", "OTHER",
    "UNKNOWN", "POLYGON", "LINESTRING", "MULTILINESTRING",
)
DIMENSION_TYPES = (
    "LINEAR", "ALIGNED", "ANGULAR", "DIAMETRIC",
    "RADIUS", "ANGULAR_3P", "ORDINATE", "UNKNOWN",
)

# Anchor kinds are deliberately compact and deterministic.
ANCHOR_TYPES = (
    "START", "END", "VERTEX", "CENTER",
    "INTERSECTION", "DIMENSION_ATTACH",
)


def _get(obj: Any, name: str, default=None):
    """Read a field from either a dataclass/object or a mapping."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _hash_bucket(token: str, size: int) -> int:
    digest = hashlib.blake2b(
        token.encode("utf-8", errors="ignore"), digest_size=8
    ).digest()
    return int.from_bytes(digest, "little") % size


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        value = float(value)
        return value if math.isfinite(value) else default
    except (TypeError, ValueError, OverflowError):
        return default


def _xy(point):
    if point is None:
        return None
    if hasattr(point, "x") and hasattr(point, "y"):
        return float(point.x), float(point.y)
    try:
        return float(point[0]), float(point[1])
    except (TypeError, ValueError, IndexError, OverflowError):
        return None


def _bounds(geometry):
    if geometry is None or getattr(geometry, "is_empty", True):
        return None
    try:
        return tuple(float(v) for v in geometry.bounds)
    except Exception:
        return None


def _line_parts(geometry):
    if geometry is None:
        return []
    if geometry.geom_type == "LineString":
        return [geometry]
    if geometry.geom_type == "MultiLineString":
        return list(geometry.geoms)
    if geometry.geom_type == "GeometryCollection":
        result = []
        for part in geometry.geoms:
            result.extend(_line_parts(part))
        return result
    if geometry.geom_type == "Polygon":
        return [geometry.exterior]
    if geometry.geom_type == "MultiPolygon":
        return [polygon.exterior for polygon in geometry.geoms]
    return []



def _arc_sweep_angle_rad(element, raw_entity=None) -> float:
    """Return a deterministic CIRCLE/ARC sweep in radians.

    DXF start_angle/end_angle are conventionally stored in degrees. Explicit
    *_rad and *_deg fields are honored first. If raw angles are unavailable,
    estimate the sweep from the ordered tessellated path around its center.
    """
    element_source = _get(element, "source")
    raw_source_for_type = _get(raw_entity, "source") if raw_entity is not None else None
    entity_type = str(
        _get(element_source, "entity_type", None)
        or _get(raw_source_for_type, "entity_type", None)
        or _get(element, "entity_type", "OTHER")
    ).upper()
    if entity_type == "CIRCLE":
        return 2.0 * math.pi
    if entity_type != "ARC":
        return 0.0

    source = element_source
    raw_source = raw_source_for_type
    containers = [element, source, raw_entity, raw_source]
    for owner in (element, source, raw_entity, raw_source):
        attrs = _get(owner, "attributes", None)
        if attrs is not None:
            containers.append(attrs)
        dxf_attrs = _get(owner, "dxf", None)
        if dxf_attrs is not None:
            containers.append(dxf_attrs)

    def read(names):
        for container in containers:
            for name in names:
                value = _get(container, name, None)
                if value is None:
                    continue
                try:
                    value = float(value)
                except (TypeError, ValueError, OverflowError):
                    continue
                if math.isfinite(value):
                    return value
        return None

    sweep = read(("sweep_angle_rad", "central_angle_rad", "included_angle_rad", "arc_angle_rad"))
    if sweep is None:
        sweep_deg = read(("sweep_angle_deg", "central_angle_deg", "included_angle_deg", "arc_angle_deg"))
        if sweep_deg is not None:
            sweep = math.radians(abs(sweep_deg))

    if sweep is None:
        start_rad = read(("start_angle_rad", "startAngleRad"))
        end_rad = read(("end_angle_rad", "endAngleRad"))
        if start_rad is not None and end_rad is not None:
            sweep = (end_rad - start_rad) % (2.0 * math.pi)
        else:
            # ezdxf and the DXF specification represent ARC start/end angles
            # in degrees, measured counter-clockwise from +X.
            start_deg = read(("start_angle_deg", "start_angle", "startAngle"))
            end_deg = read(("end_angle_deg", "end_angle", "endAngle"))
            if start_deg is not None and end_deg is not None:
                sweep = math.radians((end_deg - start_deg) % 360.0)

    if sweep is not None and math.isfinite(sweep) and sweep > 1e-9:
        return min(2.0 * math.pi, abs(float(sweep)))

    # Fallback: integrate angular changes along the ordered Shapely path.
    geometry = _get(element, "geometry_2d")
    center = _xy(_get(element, "center"))
    if center is None:
        center = _xy(_get(source, "center"))
    if center is None:
        center = _xy(_get(raw_entity, "center"))
    if center is None:
        center = _xy(_get(raw_source, "center"))
    if center is not None and geometry is not None and not getattr(geometry, "is_empty", True):
        parts = _line_parts(geometry)
        if parts:
            try:
                coords = list(parts[0].coords)
                angles = [math.atan2(float(y) - center[1], float(x) - center[0]) for x, y, *rest in coords]
                total = 0.0
                for a, b in zip(angles[:-1], angles[1:]):
                    delta = (b - a + math.pi) % (2.0 * math.pi) - math.pi
                    total += abs(delta)
                if total > 1e-9:
                    return min(2.0 * math.pi, total)
            except Exception:
                pass

    # Last-resort sweep estimate from tessellated arc length / raw DXF radius.
    radius = _safe_float(_get(element, "radius", 0.0))
    if radius <= 1e-9:
        radius = _safe_float(read(("radius",)))
    path_length = _safe_float(getattr(geometry, "length", 0.0)) if geometry is not None else 0.0
    if radius > 1e-9 and path_length > 1e-9:
        return min(2.0 * math.pi, path_length / radius)
    return 0.0

def _geometry_feature(element, scale: float, origin):
    """Build the v8 geometry vector; supervised measurements are excluded."""
    geometry = _get(element, "geometry_2d")
    bounds = _bounds(geometry)
    if bounds:
        minx, miny, maxx, maxy = bounds
        cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
        width, height = maxx - minx, maxy - miny
        try:
            vertex_count = sum(len(part.coords) for part in _line_parts(geometry))
            if vertex_count == 0 and hasattr(geometry, "exterior") and geometry.exterior:
                vertex_count = len(geometry.exterior.coords)
        except Exception:
            vertex_count = 0
    else:
        cx = cy = width = height = vertex_count = 0.0

    center_xy = _xy(_get(element, "center"))
    if center_xy:
        cx, cy = center_xy

    scale = max(abs(scale), 1e-9)
    ox, oy = origin
    geom_type = str(_get(element, "geometry_type", "OTHER")).upper()
    entity_type = str(_get(_get(element, "source"), "entity_type", "OTHER")).upper()
    type_vector = [1.0 if geom_type == item else 0.0 for item in GEOMETRY_TYPES]
    entity_hash = [0.0] * 8
    entity_hash[_hash_bucket(entity_type, 8)] = 1.0

    # Raw DXF radius is excluded: it is the supervised radius target.
    radius_raw = _get(element, "radius")
    radius_valid = radius_raw is not None and math.isfinite(
        _safe_float(radius_raw, float("nan"))
    )
    base_features = [
        (cx - ox) / scale, (cy - oy) / scale,
        width / scale, height / scale,
        math.log1p(max(0.0, vertex_count)),
        float(bool(_get(element, "is_closed", False))),
        float(bool(_get(element, "is_valid", True))),
        *type_vector, *entity_hash, float(radius_valid),
    ]
    return base_features + extract_geometry_descriptors(element, scale)
def _dimension_feature(dimension, scale: float, origin):
    """Build 17 dimension features, including endpoint direction and value-validity flags."""
    scale = max(abs(scale), 1e-9)
    endpoints = _get(dimension, "endpoints")
    p1 = _xy(endpoints[0]) if endpoints else None
    p2 = _xy(endpoints[1]) if endpoints else None
    if p1 and p2:
        mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
        dx, dy = (p2[0] - p1[0]) / scale, (p2[1] - p1[1]) / scale
        span = math.hypot(dx, dy)
    else:
        mx = my = dx = dy = span = 0.0
    center = _xy(_get(dimension, "center"))
    if center:
        mx, my = center
    ox, oy = origin
    kind = str(_get(dimension, "dimension_type", "UNKNOWN")).upper()
    onehot = [1.0 if kind == item else 0.0 for item in DIMENSION_TYPES]
    value = _get(dimension, "length")
    actual = _get(dimension, "actual_length")
    value_valid = value is not None and math.isfinite(_safe_float(value, float("nan")))
    actual_valid = actual is not None and math.isfinite(_safe_float(actual, float("nan")))
    return [
        _safe_float(value) / scale,
        _safe_float(actual) / scale,
        span,
        (mx - ox) / scale,
        (my - oy) / scale,
        dx, dy,
        *onehot,
        float(value_valid), float(actual_valid),
    ]


def _text_feature(text, scale: float, origin, lexical_size: int = 32, text_config=None):
    content = str(_get(text, "text", "") or "")
    config = text_config or {}
    normalized = normalize_text(content, config)
    semantic_categories, _ = classify_text_categories(normalized, config)
    position = _xy(_get(text, "position")) or _xy(_get(text, "position_moved"))
    if position is None:
        position = (0.0, 0.0)
    bound = _get(text, "bound") or _get(text, "bound_moved")
    bounds = _bounds(bound)
    width, height = (bounds[2] - bounds[0], bounds[3] - bounds[1]) if bounds else (0.0, 0.0)
    scale = max(abs(scale), 1e-9)
    ox, oy = origin
    lexical = [0.0] * lexical_size
    for token in tokenize_text(normalized, config):
        lexical[_hash_bucket(token, lexical_size)] += 1.0
    norm = max(1.0, math.sqrt(sum(v * v for v in lexical)))
    lexical = [v / norm for v in lexical]
    evidence = parse_measurement_evidence(normalized, config)
    category_features = [
        float(category in semantic_categories) for category in TEXT_CATEGORIES
    ]
    return [
        (position[0] - ox) / scale, (position[1] - oy) / scale,
        width / scale, height / scale, _safe_float(_get(text, "angle", 0.0)),
        math.log1p(len(normalized)),
        math.log1p(sum(ch.isdigit() for ch in normalized)),
        float(evidence["has_diameter_symbol"]),
        float(evidence["has_radius_symbol"]),
        *category_features,
        *lexical,
    ]


def _raw_text_items(raw_entities):
    """Include text-like RawEntity records not already represented by TextElement."""
    for raw in raw_entities or []:
        source = _get(raw, "source")
        entity_type = str(_get(source, "entity_type", "")).upper()
        if entity_type not in {"TEXT", "MTEXT", "ATTRIB", "ATTDEF"}:
            continue
        content = _get(raw, "text")
        if not content:
            continue
        attrs = _get(raw, "attributes", {}) or {}
        position = attrs.get("center") or attrs.get("insert") or attrs.get("position")
        corners = attrs.get("corners")
        bound = None
        if corners and len(corners) >= 3:
            try:
                from shapely.geometry import Polygon
                bound = Polygon([(p[0], p[1]) for p in corners])
            except Exception:
                bound = None
        yield {
            "element_id": _get(source, "entity_handle", ""),
            "source_handle": _get(source, "entity_handle", ""),
            "source": source,
            "text": content,
            "position": Point(position[0], position[1]) if position else None,
            "position_moved": None,
            "bound": bound,
            "bound_moved": None,
            "angle": math.radians(_safe_float(attrs.get("angle", 0.0))),
        }


def _add_edge(edge_store, edge_type, source_idx, target_idx, attrs):
    """Append one typed edge with a numeric feature vector."""
    edge_store[edge_type].append(
        (int(source_idx), int(target_idx), [_safe_float(v) for v in attrs])
    )


def _angle_between(v1, v2):
    if v1 is None or v2 is None:
        return None
    dot = max(-1.0, min(1.0, v1[0] * v2[0] + v1[1] * v2[1]))
    # Direction is unoriented for CAD line parallelism.
    return math.acos(min(1.0, abs(dot)))


def _segment_records(geometry):
    records = []
    for part in _line_parts(geometry):
        coords = list(part.coords)
        for a, b in zip(coords[:-1], coords[1:]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            length = math.hypot(dx, dy)
            if length > 1e-9:
                records.append({
                    "start": (float(a[0]), float(a[1])),
                    "end": (float(b[0]), float(b[1])),
                    "length": length,
                    "direction": (dx / length, dy / length),
                })
    return records


def _endpoint_points(geometry):
    points = []
    if geometry is not None and geometry.geom_type in {"Polygon", "MultiPolygon"}:
        return points
    for part in _line_parts(geometry):
        coords = list(part.coords)
        if len(coords) >= 2:
            points.extend([Point(coords[0]), Point(coords[-1])])
    if geometry is not None and geometry.geom_type == "Point":
        points.append(geometry)
    return points


def _representative_direction(geometry, angular_tolerance_degrees=3.0):
    # A single orientation is meaningful only for a straight open line.
    # Do not infer one from a circle, closed profile, bent polyline, or arc.
    if geometry is None or geometry.geom_type != "LineString":
        return None
    segments = _segment_records(geometry)
    if not segments:
        return None
    reference = max(segments, key=lambda item: item["length"])["direction"]
    tolerance = math.radians(max(0.0, angular_tolerance_degrees))
    if any(
        (_angle_between(reference, segment["direction"]) or 0.0) > tolerance
        for segment in segments
    ):
        return None
    return reference


def _collinear_score(geometry_a, geometry_b, direction_a, direction_b, tolerance, angular_tolerance_degrees=3.0):
    if direction_a is None or direction_b is None:
        return 0.0
    angle = _angle_between(direction_a, direction_b)
    if angle is None or angle > math.radians(max(0.0, angular_tolerance_degrees)):
        return 0.0
    segments_a = _segment_records(geometry_a)
    segments_b = _segment_records(geometry_b)
    if not segments_a or not segments_b:
        return 0.0
    a = max(segments_a, key=lambda item: item["length"])
    b = max(segments_b, key=lambda item: item["length"])
    dx, dy = b["start"][0] - a["start"][0], b["start"][1] - a["start"][1]
    perpendicular = abs(dx * direction_a[1] - dy * direction_a[0])
    if perpendicular > max(tolerance, 1e-9):
        return 0.0
    return max(0.0, 1.0 - perpendicular / max(tolerance, 1e-9))


def _intersection_point_coords(geometry):
    """Return point-like coordinates from a Shapely intersection result."""
    if geometry is None or geometry.is_empty:
        return []
    if geometry.geom_type == "Point":
        return [(float(geometry.x), float(geometry.y))]
    if geometry.geom_type in {"MultiPoint", "GeometryCollection"}:
        points = []
        for part in geometry.geoms:
            points.extend(_intersection_point_coords(part))
        return points
    # For overlapping linework, the overlap endpoints are useful anchors.
    if geometry.geom_type == "LineString":
        coords = list(geometry.coords)
        return [(float(coords[0][0]), float(coords[0][1])),
                (float(coords[-1][0]), float(coords[-1][1]))] if len(coords) >= 2 else []
    if geometry.geom_type == "MultiLineString":
        points = []
        for part in geometry.geoms:
            points.extend(_intersection_point_coords(part))
        return points
    return []


def _unit_direction(a, b):
    dx, dy = float(b[0]) - float(a[0]), float(b[1]) - float(a[1])
    length = math.hypot(dx, dy)
    return (dx / length, dy / length) if length > 1e-9 else (0.0, 0.0)


def _local_curvature_summary(geometry):
    values = []
    for part in _line_parts(geometry):
        coords = [(float(p[0]), float(p[1])) for p in part.coords]
        for index in range(1, len(coords) - 1):
            incoming = _unit_direction(coords[index - 1], coords[index])
            outgoing = _unit_direction(coords[index], coords[index + 1])
            dot = max(-1.0, min(1.0, incoming[0] * outgoing[0] + incoming[1] * outgoing[1]))
            cross = incoming[0] * outgoing[1] - incoming[1] * outgoing[0]
            length = 0.5 * (math.dist(coords[index - 1], coords[index]) + math.dist(coords[index], coords[index + 1]))
            if length > 1e-9:
                values.append(math.atan2(cross, dot) / length)
    if not values:
        return None
    values.sort()
    return values[len(values) // 2]


def _anchor_specs(element):
    """Create anchors with local tangent and signed discrete curvature."""
    geom = _get(element, "geometry_2d")
    if geom is None or geom.is_empty:
        return []
    specs = []
    entity_type = str(_get(_get(element, "source"), "entity_type", "")).upper()
    center = _xy(_get(element, "center"))
    if center is None:
        c = geom.centroid
        center = (float(c.x), float(c.y))
    if entity_type in {"CIRCLE", "ARC"}:
        # Estimate curvature from tessellated geometry, not raw DXF radius,
        # to avoid leaking the supervised radius target into model inputs.
        curvature = _local_curvature_summary(geom) or 0.0
        specs.append((center, "CENTER", (0.0, 0.0), curvature))
    if entity_type == "CIRCLE":
        return specs
    if geom.geom_type == "Point":
        p = _xy(geom)
        return [(p, "CENTER", (0.0, 0.0), 0.0)] if p else specs
    for part in _line_parts(geom):
        coords = [(float(p[0]), float(p[1])) for p in part.coords]
        if len(coords) < 2:
            continue
        specs.append((coords[0], "START", _unit_direction(coords[0], coords[1]), 0.0))
        specs.append((coords[-1], "END", _unit_direction(coords[-2], coords[-1]), 0.0))
        for index in range(1, len(coords) - 1):
            incoming = _unit_direction(coords[index - 1], coords[index])
            outgoing = _unit_direction(coords[index], coords[index + 1])
            dot = max(-1.0, min(1.0, incoming[0] * outgoing[0] + incoming[1] * outgoing[1]))
            cross = incoming[0] * outgoing[1] - incoming[1] * outgoing[0]
            turn = math.atan2(cross, dot)
            length = 0.5 * (math.dist(coords[index - 1], coords[index]) + math.dist(coords[index], coords[index + 1]))
            tangent_sum = (incoming[0] + outgoing[0], incoming[1] + outgoing[1])
            tangent_norm = math.hypot(*tangent_sum)
            tangent = (tangent_sum[0] / tangent_norm, tangent_sum[1] / tangent_norm) if tangent_norm > 1e-9 else outgoing
            specs.append((coords[index], "VERTEX", tangent, turn / max(length, 1e-9)))
    unique, seen = [], set()
    for coord, kind, tangent, curvature in specs:
        key = (round(coord[0], 8), round(coord[1], 8))
        if key not in seen:
            seen.add(key)
            unique.append((coord, kind, tangent, curvature))
    return unique


def _anchor_feature(coord, kind, tangent, curvature, scale, origin, center):
    scale = max(abs(scale), 1e-9)
    ox, oy = origin
    type_vector = [1.0 if kind == item else 0.0 for item in ANCHOR_TYPES]
    center_distance = (
        math.hypot(coord[0] - center[0], coord[1] - center[1]) / scale
        if center else 0.0
    )
    return [
        (coord[0] - ox) / scale,
        (coord[1] - oy) / scale,
        *type_vector,
        _safe_float(tangent[0] if tangent else 0.0),
        _safe_float(tangent[1] if tangent else 0.0),
        _safe_float(curvature),
        center_distance,
    ]


def _make_relation_attrs(distance, angle_diff, intersection_length,
                         endpoint_distance, overlap_ratio, confidence, scale,
                         tangent_continuity=0.0, curvature_similarity=0.0,
                         collinear_score=0.0):
    scale = max(abs(scale), 1e-9)
    return [
        _safe_float(distance) / scale,
        _safe_float(angle_diff) / math.pi if angle_diff is not None else 0.0,
        _safe_float(intersection_length) / scale,
        _safe_float(endpoint_distance) / scale,
        _safe_float(overlap_ratio),
        max(0.0, min(1.0, _safe_float(confidence))),
        float(endpoint_distance is not None and math.isfinite(_safe_float(endpoint_distance, float("nan")))),
        max(0.0, min(1.0, _safe_float(tangent_continuity))),
        max(0.0, min(1.0, _safe_float(curvature_similarity))),
        max(0.0, min(1.0, _safe_float(collinear_score))),
    ]


def build_semantic_graph(
    geometry_elements,
    dimension_elements,
    text_elements,
    raw_entities=None,
    analytic_graph=None,
    spatial_index=None,
    scale: float = 1.0,
    spatial_tolerance: float = 300.0,
    dimension_tolerance: float = 2000.0,
    text_tolerance: float = 300.0,
    max_neighbors: int = 16,
    connection_tolerance: float = 200.0,
    angular_tolerance_degrees: float = 3.0,
    collinear_tolerance: float = 20.0,
    mirror_tolerance: float = 5.0,
    tangent_tolerance_degrees: float = 12.0,
    curvature_tolerance: float = 0.02,
    text_config_path: str | None = None,
    relation_search_tolerance: float | None = None,
    global_relation_max_neighbors: int = 24,
    text_candidate_search_tolerance: float | None = None,
):
    """Build a DXF engineering HeteroData graph.

    Geometry nodes use the 24-value v6 prefix plus 21 versioned v8 shape
    descriptors (45 inputs total). Text nodes use 47 multi-hot/lexical features,
    and text-to-geometry edges use 39 features.
    The graph also includes anchors, dimension-to-geometry/anchor candidates,
    and dimension-to-dimension candidate relationships.

    Analytical length and area remain metadata only: they are never included
    in geometry.x. Independent reviewed regression targets are attached later
    by ai_gnn.labels and consumed by the multi-task GNN.
    """
    try:
        import torch
        from torch_geometric.data import HeteroData
    except ImportError as exc:
        raise ImportError(
            "PyTorch Geometric is required for the AI graph. Install the "
            "PyTorch build matching your environment, then install "
            "`torch-geometric`."
        ) from exc

    geometry_elements = list(geometry_elements or [])
    dimension_elements = list(dimension_elements or [])
    text_elements = list(text_elements or [])
    text_config = load_text_config(text_config_path)

    # Prefer rich TextElement instances, then include extracted raw MTEXT,
    # ATTRIB and ATTDEF records not represented by those objects.
    known_text_handles = {str(_get(t, "source_handle", "")) for t in text_elements}
    for item in _raw_text_items(raw_entities):
        if str(_get(item, "source_handle", "")) not in known_text_handles:
            text_elements.append(item)

    scale_safe = max(abs(_safe_float(scale, 1.0)), 1e-9)
    all_points = []
    for item in geometry_elements:
        b = _bounds(_get(item, "geometry_2d"))
        if b:
            all_points.append(((b[0] + b[2]) / 2, (b[1] + b[3]) / 2))
    for item in dimension_elements:
        ep = _get(item, "endpoints")
        if ep:
            all_points.extend([p for p in (_xy(ep[0]), _xy(ep[1])) if p])
        definition_points = _get(item, "definition_points")
        if definition_points:
            all_points.extend([p for p in (_xy(point) for point in definition_points) if p])
        for field in ("center", "measurement_point"):
            p = _xy(_get(item, field))
            if p:
                all_points.append(p)
    for item in text_elements:
        p = _xy(_get(item, "position")) or _xy(_get(item, "position_moved"))
        if p:
            all_points.append(p)
    origin = (
        (min(p[0] for p in all_points), min(p[1] for p in all_points))
        if all_points else (0.0, 0.0)
    )

    data = HeteroData()

    def feature_tensor(rows, width):
        if not rows:
            return torch.empty((0, width), dtype=torch.float)
        return torch.tensor(rows, dtype=torch.float).reshape(len(rows), width)

    data["geometry"].x = feature_tensor(
        [_geometry_feature(x, scale_safe, origin) for x in geometry_elements], 24 + len(GEOMETRY_FEATURE_NAMES)
    )
    data["dimension"].x = feature_tensor(
        [_dimension_feature(x, scale_safe, origin) for x in dimension_elements], 17
    )
    data["text"].x = feature_tensor(
        [_text_feature(x, scale_safe, origin, text_config=text_config) for x in text_elements],
        len(TEXT_FEATURE_NAMES),
    )

    # Preserve traceability and expose exact deterministic geometry values.
    for node_type, items in (
        ("geometry", geometry_elements),
        ("dimension", dimension_elements),
        ("text", text_elements),
    ):
        data[node_type].element_id = [str(_get(x, "element_id", "")) for x in items]
        data[node_type].source_handle = [
            str(_get(x, "source_handle", "") or _get(_get(x, "source"), "entity_handle", ""))
            for x in items
        ]
        data[node_type].source_layer = [
            str(_get(_get(x, "source"), "layer", "")) for x in items
        ]

    data["geometry"].entity_type = [
        str(_get(_get(x, "source"), "entity_type", "OTHER")).upper()
        for x in geometry_elements
    ]
    raw_entity_by_handle = {}
    for raw in raw_entities or []:
        raw_source = _get(raw, "source")
        raw_handle = str(
            _get(raw, "source_handle", "")
            or _get(raw_source, "entity_handle", "")
            or _get(raw, "handle", "")
        ).strip().upper()
        if raw_handle:
            raw_entity_by_handle[raw_handle] = raw
    data["geometry"].arc_sweep_angle_rad = [
        _arc_sweep_angle_rad(
            item,
            raw_entity_by_handle.get(str(
                _get(item, "source_handle", "")
                or _get(_get(item, "source"), "entity_handle", "")
            ).strip().upper()),
        )
        for item in geometry_elements
    ]
    data["geometry"].arc_sweep_angle_valid = torch.tensor(
        [value > 1e-9 for value in data["geometry"].arc_sweep_angle_rad],
        dtype=torch.bool,
    )
    data["geometry"].geometry_type = [
        str(_get(x, "geometry_type", "OTHER")).upper()
        for x in geometry_elements
    ]
    data["geometry"].is_closed = torch.tensor(
        [bool(_get(x, "is_closed", False)) for x in geometry_elements], dtype=torch.bool
    )
    def optional_measurement(item, field):
        raw = _get(item, field)
        try:
            value = float(raw)
            return value if math.isfinite(value) else 0.0
        except (TypeError, ValueError, OverflowError):
            return 0.0

    data["geometry"].measured_length = [optional_measurement(x, "length") for x in geometry_elements]
    data["geometry"].measured_area = [optional_measurement(x, "area") for x in geometry_elements]
    # Raw Shapely geometry measurements are retained as non-learned metadata.
    # Area prediction is derived from corrected length and raw shape scale;
    # these values are never concatenated into geometry.x.
    def raw_shape_area(item):
        geom = _get(item, "geometry_2d")
        if geom is None or getattr(geom, "is_empty", True):
            return 0.0
        try:
            if geom.geom_type in {"Polygon", "MultiPolygon"}:
                return _safe_float(geom.area)
            if bool(_get(item, "is_closed", False)) and geom.geom_type in {"LineString", "LinearRing"}:
                from shapely.geometry import Polygon
                polygon = Polygon(geom)
                return _safe_float(polygon.area) if polygon.is_valid else 0.0
        except Exception:
            pass
        return 0.0

    data["geometry"].raw_geometry_perimeter = [
        _safe_float(getattr(_get(x, "geometry_2d"), "length", 0.0))
        for x in geometry_elements
    ]
    data["geometry"].raw_geometry_area = [raw_shape_area(x) for x in geometry_elements]
    # radius is the raw DXF entity radius; analytic radius_measured is separate.
    data["geometry"].radius = [optional_measurement(x, "radius") for x in geometry_elements]
    data["geometry"].radius_measured = [optional_measurement(x, "radius_measured") for x in geometry_elements]
    def valid_source_value(item, field):
        raw = _get(item, field)
        try:
            return raw is not None and math.isfinite(float(raw))
        except (TypeError, ValueError, OverflowError):
            return False
    data["geometry"].measured_length_valid = torch.tensor(
        [valid_source_value(x, "length") for x in geometry_elements], dtype=torch.bool
    )
    data["geometry"].measured_area_valid = torch.tensor(
        [valid_source_value(x, "area") for x in geometry_elements], dtype=torch.bool
    )
    data["geometry"].radius_valid = torch.tensor(
        [valid_source_value(x, "radius") for x in geometry_elements], dtype=torch.bool
    )
    data["dimension"].dimension_type = [
        str(_get(x, "dimension_type", "UNKNOWN")) for x in dimension_elements
    ]
    data["dimension"].display_value = [
        _safe_float(_get(x, "length"), float("nan")) for x in dimension_elements
    ]
    data["dimension"].actual_value = [
        _safe_float(_get(x, "actual_length"), float("nan")) for x in dimension_elements
    ]
    data["dimension"].definition_points = [
        [
            _xy(point) for point in (
                _get(x, "definition_points")
                or _get(x, "endpoints")
                or ()
            )
        ] for x in dimension_elements
    ]
    data["text"].content = [
        str(_get(x, "text", "") or "") for x in text_elements
    ]

    geom_by_handle = {
        str(_get(x, "source_handle", "") or _get(_get(x, "source"), "entity_handle", "")): i
        for i, x in enumerate(geometry_elements)
    }

    # Build an STRtree fallback when the application does not supply its own
    # spatial index. This prevents a full all-pairs scan for wider relation
    # searches on large drawings.
    tree_geometries = [
        _get(item, "geometry_2d") for item in geometry_elements
        if _get(item, "geometry_2d") is not None
        and not getattr(_get(item, "geometry_2d"), "is_empty", True)
    ]
    tree_indices = [
        i for i, item in enumerate(geometry_elements)
        if _get(item, "geometry_2d") is not None
        and not getattr(_get(item, "geometry_2d"), "is_empty", True)
    ]
    geometry_tree = None
    tree_id_to_indices = defaultdict(list)
    if tree_geometries:
        try:
            geometry_tree = STRtree(tree_geometries)
            for idx, geom in zip(tree_indices, tree_geometries):
                tree_id_to_indices[id(geom)].append(idx)
        except Exception:
            geometry_tree = None

    def candidate_geometry_indices(query, distance):
        if query is None or getattr(query, "is_empty", False):
            return []
        if spatial_index is not None:
            try:
                candidates = spatial_index.nearby(
                    query, distance=distance, exclude_handle=None
                )
                indices = []
                for candidate in candidates:
                    handle = str(
                        _get(candidate, "source_handle", "")
                        or _get(_get(candidate, "source"), "entity_handle", "")
                    )
                    index = geom_by_handle.get(handle)
                    if index is not None:
                        indices.append(index)
                return sorted(set(indices))
            except Exception:
                pass
        if geometry_tree is not None:
            try:
                queried = geometry_tree.query(query.buffer(float(distance)))
                indices = []
                for candidate in queried:
                    # Shapely 2 returns integer indices; Shapely 1 returns
                    # geometry objects.
                    if isinstance(candidate, (int,)) or type(candidate).__module__.startswith("numpy"):
                        pos = int(candidate)
                        if 0 <= pos < len(tree_indices):
                            indices.append(tree_indices[pos])
                    else:
                        indices.extend(tree_id_to_indices.get(id(candidate), []))
                return sorted(set(indices))
            except Exception:
                pass
        return range(len(geometry_elements))

    edge_store = defaultdict(list)
    gcount, dcount, tcount = len(geometry_elements), len(dimension_elements), len(text_elements)

    # --------------------------------------------------------------
    # Phase 1: Geometry-to-geometry semantic relations
    # --------------------------------------------------------------
    # Keep the existing analytical-graph proximity edges.
    if analytic_graph is not None:
        for u, v, attrs in analytic_graph.edges(data=True):
            if not (isinstance(u, tuple) and isinstance(v, tuple)
                    and u[0] == "G" and v[0] == "G"):
                continue
            # The existing topology graph can contain endpoint-connected,
            # crossing, and other relations. Do not relabel those as `near`.
            analytic_relation = str(attrs.get("relationship", "near")).lower()
            if analytic_relation not in {"near", "spatial_candidate"}:
                continue
            ui = geom_by_handle.get(str(u[1]))
            vi = geom_by_handle.get(str(v[1]))
            if ui is None or vi is None or ui == vi:
                continue
            ga = _get(geometry_elements[ui], "geometry_2d")
            gb = _get(geometry_elements[vi], "geometry_2d")
            distance = _safe_float(attrs.get("distance", 0.0))
            _add_edge(
                edge_store, ("geometry", "near", "geometry"), ui, vi,
                _make_relation_attrs(
                    distance, None, 0.0, float("inf"), 0.0,
                    attrs.get("confidence", 1.0), scale_safe
                ),
            )

    angular_tol = math.radians(max(0.0, angular_tolerance_degrees))
    tangent_tol = math.radians(max(0.0, tangent_tolerance_degrees))
    pair_seen = set()
    relation_search_tolerance = (
        max(float(spatial_tolerance), float(relation_search_tolerance))
        if relation_search_tolerance is not None
        else max(float(spatial_tolerance) * 5.0, float(spatial_tolerance))
    )
    global_relation_max_neighbors = max(1, int(global_relation_max_neighbors))
    text_candidate_search_tolerance = (
        max(float(text_tolerance), float(text_candidate_search_tolerance))
        if text_candidate_search_tolerance is not None
        else max(float(text_tolerance) * 5.0, float(text_tolerance))
    )

    for i, a in enumerate(geometry_elements):
        ga = _get(a, "geometry_2d")
        if ga is None or ga.is_empty:
            continue
        candidate_indices = candidate_geometry_indices(ga, relation_search_tolerance)
        # Preserve every local spatial candidate, plus only the nearest bounded
        # set of wider candidates for equal-length/mirror discovery.
        scored_candidates = []
        for candidate_j in candidate_indices:
            if candidate_j <= i:
                continue
            candidate_geom = _get(geometry_elements[candidate_j], "geometry_2d")
            if candidate_geom is None or candidate_geom.is_empty:
                continue
            try:
                candidate_distance = float(ga.distance(candidate_geom))
            except Exception:
                continue
            if candidate_distance <= relation_search_tolerance:
                scored_candidates.append((candidate_distance, candidate_j))
        local_candidates = [
            item for item in scored_candidates if item[0] <= spatial_tolerance
        ]
        wider_candidates = sorted(
            item for item in scored_candidates if item[0] > spatial_tolerance
        )[:global_relation_max_neighbors]
        selected_candidates = sorted(local_candidates + wider_candidates)
        for candidate_distance, j in selected_candidates:
            if j <= i:
                continue
            b = geometry_elements[j]
            gb = _get(b, "geometry_2d")
            if gb is None or gb.is_empty:
                continue

            try:
                distance = candidate_distance
                intersects = bool(ga.intersects(gb))
                touches = bool(ga.touches(gb))
                overlaps = bool(ga.overlaps(gb))
                contains = bool(ga.contains(gb))
                within = bool(ga.within(gb))
                intersection = ga.intersection(gb) if intersects else None
                intersection_length = float(intersection.length) if intersection is not None else 0.0
                intersection_area = float(intersection.area) if intersection is not None else 0.0
                union_measure = max(float(ga.area), float(gb.area), 1e-9)
                overlap_ratio = intersection_area / union_measure if intersection_area else (
                    intersection_length / max(min(float(ga.length), float(gb.length)), 1e-9)
                    if intersection_length else 0.0
                )
            except Exception:
                continue

            dir_a = _representative_direction(ga, angular_tolerance_degrees)
            dir_b = _representative_direction(gb, angular_tolerance_degrees)
            angle_diff = _angle_between(dir_a, dir_b)
            endpoints_a = _endpoint_points(ga)
            endpoints_b = _endpoint_points(gb)
            endpoint_distance = min(
                (pa.distance(pb) for pa in endpoints_a for pb in endpoints_b),
                default=float("inf"),
            )
            collinear_score = _collinear_score(
                ga, gb, dir_a, dir_b, collinear_tolerance,
                angular_tolerance_degrees,
            )
            seg_a, seg_b = _segment_records(ga), _segment_records(gb)
            tangent_continuity = 0.0
            curvature_similarity = 0.0
            if seg_a and seg_b:
                # Compare the closest actual segment pair, not only endpoint
                # distances. The latter can select the wrong pair when two
                # long segments approach or cross near their interiors.
                sa, sb = min(
                    ((x, y) for x in seg_a for y in seg_b),
                    key=lambda pair: LineString([
                        pair[0]["start"], pair[0]["end"]
                    ]).distance(LineString([
                        pair[1]["start"], pair[1]["end"]
                    ])),
                )
                tangent_a, tangent_b = sa["direction"], sb["direction"]

                # Tessellated circles/arcs approximate a smooth curve with
                # chords. Comparing the chord directions directly introduces
                # a quantization error (for example, 2.8 degrees for a
                # 128-segment circle) even when the true local tangents agree.
                # Recover the tangent at the nearest boundary point from the
                # radial direction for circular entities; retain segment
                # tangents for lines and other non-circular geometry.
                try:
                    nearest_a, nearest_b = nearest_points(ga, gb)
                    for item, nearest, fallback, slot in (
                        (a, nearest_a, tangent_a, 0),
                        (b, nearest_b, tangent_b, 1),
                    ):
                        entity_type = str(
                            _get(_get(item, "source"), "entity_type", "")
                        ).upper()
                        if entity_type not in {"CIRCLE", "ARC"}:
                            continue
                        center = _xy(_get(item, "center"))
                        if center is None:
                            centroid = _get(item, "geometry_2d").centroid
                            center = (float(centroid.x), float(centroid.y))
                        radial = _unit_direction(center, (nearest.x, nearest.y))
                        if math.hypot(*radial) <= 1e-9:
                            continue
                        local_tangent = (-radial[1], radial[0])
                        if slot == 0:
                            tangent_a = local_tangent
                        else:
                            tangent_b = local_tangent
                except Exception:
                    pass

                tangent_angle = _angle_between(tangent_a, tangent_b)
                if tangent_angle is not None:
                    tangent_continuity = max(0.0, 1.0 - tangent_angle / max(tangent_tol, 1e-9))
                curvature_a, curvature_b = _local_curvature_summary(ga), _local_curvature_summary(gb)
                if curvature_a is not None and curvature_b is not None:
                    curvature_delta = min(abs(curvature_a - curvature_b), abs(curvature_a + curvature_b))
                    curvature_similarity = math.exp(-curvature_delta / max(curvature_tolerance, 1e-9))

            relation_records = []
            if distance <= spatial_tolerance:
                relation_records.append(("near", max(0.0, 1.0 - distance / max(spatial_tolerance, 1e-9))))
            if angle_diff is not None and angle_diff <= angular_tol:
                relation_records.append(("parallel", max(0.0, 1.0 - angle_diff / max(angular_tol, 1e-9))))
            if angle_diff is not None and abs((math.pi / 2) - angle_diff) <= angular_tol:
                relation_records.append(("perpendicular", max(0.0, 1.0 - abs((math.pi / 2) - angle_diff) / max(angular_tol, 1e-9))))
            if intersects:
                relation_records.append(("intersects", 1.0))
            if touches:
                relation_records.append(("touches", 1.0))
            if overlaps:
                relation_records.append(("overlaps", 1.0))
            if contains:
                relation_records.append(("contains", 1.0))
            if within:
                relation_records.append(("within", 1.0))
            if endpoint_distance <= max(connection_tolerance, 0.0):
                relation_records.append((
                    "connected",
                    max(0.0, 1.0 - endpoint_distance / max(connection_tolerance, 1e-9))
                    if connection_tolerance > 0 else 1.0,
                ))
            if collinear_score > 0.0:
                relation_records.append(("collinear", collinear_score))

            # Local topology remains bounded by spatial_tolerance. The wider
            # search is used only for equal-length and mirror candidates.
            if distance <= spatial_tolerance:
                for relation, confidence in relation_records:
                    edge_type = ("geometry", relation, "geometry")
                    attrs = _make_relation_attrs(
                        distance, angle_diff, intersection_length,
                        endpoint_distance, overlap_ratio, confidence, scale_safe,
                        tangent_continuity, curvature_similarity, collinear_score,
                    )
                    _add_edge(edge_store, edge_type, i, j, attrs)
                    pair_seen.add((i, j, relation))

            # Candidate geometric constraints. These are evidence edges, not
            # asserted engineering equalities or symmetry constraints.
            length_a, length_b = float(ga.length), float(gb.length)
            if min(length_a, length_b) > 1e-9:
                length_delta = abs(length_a - length_b) / max(length_a, length_b)
                if length_delta <= 0.02:
                    bounds_a, bounds_b = _bounds(ga), _bounds(gb)
                    diagonal_a = (
                        math.hypot(bounds_a[2] - bounds_a[0], bounds_a[3] - bounds_a[1])
                        if bounds_a else 0.0
                    )
                    diagonal_b = (
                        math.hypot(bounds_b[2] - bounds_b[0], bounds_b[3] - bounds_b[1])
                        if bounds_b else 0.0
                    )
                    # Keep only dimensionless shape descriptors; do not expose
                    # the absolute Shapely lengths that the model is correcting.
                    shape_ratio_a = length_a / max(diagonal_a, 1e-9)
                    shape_ratio_b = length_b / max(diagonal_b, 1e-9)
                    _add_edge(
                        edge_store, ("geometry", "equal_length_candidate", "geometry"),
                        i, j, [length_delta, shape_ratio_a, shape_ratio_b],
                    )
            try:
                from shapely.affinity import rotate as affine_rotate
                from shapely.affinity import scale as affine_scale
                ca, cb = ga.centroid, gb.centroid
                midpoint = ((float(ca.x) + float(cb.x)) * 0.5, (float(ca.y) + float(cb.y)) * 0.5)
                mirror_tol = max(float(mirror_tolerance), 1e-6)
                best_mirror = None
                # Search the full unoriented 180-degree axis range, including
                # horizontal, vertical, diagonal and arbitrary orientations.
                # Coarse global search prevents a vertical/horizontal bias.
                # Refine around the best coarse axis so diagonal and arbitrary
                # orientations are not quantized to 5-degree increments.
                for axis_degrees in range(0, 180, 5):
                    rotated = affine_rotate(gb, -axis_degrees, origin=midpoint)
                    reflected = affine_scale(rotated, xfact=1.0, yfact=-1.0, origin=midpoint)
                    reflected = affine_rotate(reflected, axis_degrees, origin=midpoint)
                    error = float(ga.hausdorff_distance(reflected))
                    if best_mirror is None or error < best_mirror[0]:
                        best_mirror = (error, axis_degrees)
                if best_mirror is not None:
                    coarse_axis = best_mirror[1]
                    for axis_degrees in range(coarse_axis - 5, coarse_axis + 6):
                        axis_degrees %= 180
                        rotated = affine_rotate(gb, -axis_degrees, origin=midpoint)
                        reflected = affine_scale(rotated, xfact=1.0, yfact=-1.0, origin=midpoint)
                        reflected = affine_rotate(reflected, axis_degrees, origin=midpoint)
                        error = float(ga.hausdorff_distance(reflected))
                        if error < best_mirror[0]:
                            best_mirror = (error, axis_degrees)
                if best_mirror and best_mirror[0] <= mirror_tol:
                    error, axis_degrees = best_mirror
                    _add_edge(edge_store, ("geometry", "mirror_candidate", "geometry"), i, j, [
                        error / scale_safe, axis_degrees / 180.0,
                        midpoint[0] / scale_safe, midpoint[1] / scale_safe,
                        max(0.0, 1.0 - error / mirror_tol),
                    ])
            except Exception:
                pass

    # Preserve directed near edges from the original implementation and
    # analytic graph. Deduplicate all same-direction relation records.
    for edge_type, records in list(edge_store.items()):
        dedup = {}
        for src, dst, attrs in records:
            key = (src, dst)
            previous = dedup.get(key)
            score_index = 5 if len(attrs) >= 7 else len(attrs) - 1
            if previous is None or attrs[score_index] > previous[score_index]:
                dedup[key] = attrs
        edge_store[edge_type] = [
            (src, dst, attrs) for (src, dst), attrs in dedup.items()
        ]

    def dimension_geometry_attrs(distance, dimension, element):
        kind = str(_get(dimension, "dimension_type", "UNKNOWN")).upper()
        value, actual = _get(dimension, "length"), _get(dimension, "actual_length")
        try:
            value_valid = value is not None and math.isfinite(float(value))
        except (TypeError, ValueError, OverflowError):
            value_valid = False
        try:
            actual_valid = actual is not None and math.isfinite(float(actual))
        except (TypeError, ValueError, OverflowError):
            actual_valid = False
        entity = str(_get(_get(element, "source"), "entity_type", "OTHER")).upper()
        return [
            distance / scale_safe,
            max(0.0, 1.0 - distance / max(dimension_tolerance, 1e-9)),
            float(kind == "DIAMETRIC"), float(kind == "RADIUS"),
            float(kind in {"LINEAR", "ALIGNED", "ORDINATE"}),
            float(kind in {"ANGULAR", "ANGULAR_3P"}),
            float(value_valid), _safe_float(value) / scale_safe,
            float(actual_valid), _safe_float(actual) / scale_safe,
            float(entity in {"CIRCLE", "ARC"}),
            float(bool(_get(element, "is_closed", False))),
        ]

    # --------------------------------------------------------------
    # Phase 2: Geometry anchors and dimension measurement references
    # --------------------------------------------------------------
    anchor_rows = []
    anchor_owner = []
    anchor_coords = []
    anchor_kinds = []
    anchor_tangents = []
    geometry_centers = []

    for gi, element in enumerate(geometry_elements):
        geom = _get(element, "geometry_2d")
        center = None
        if geom is not None and not geom.is_empty:
            c = _xy(_get(element, "center"))
            if c is None:
                centroid = geom.centroid
                c = (float(centroid.x), float(centroid.y))
            center = c
        geometry_centers.append(center)
        for coord, kind, tangent, curvature in _anchor_specs(element):
            anchor_idx = len(anchor_rows)
            anchor_rows.append(_anchor_feature(
                coord, kind, tangent, curvature, scale_safe, origin, center
            ))
            anchor_owner.append(gi)
            anchor_coords.append(coord)
            anchor_kinds.append(kind)
            anchor_tangents.append(tangent)
            _add_edge(
                edge_store, ("geometry", "has_anchor", "anchor"),
                gi, anchor_idx, [0.0, 1.0],
            )

    # Reuse an existing endpoint/vertex/center anchor when the projected
    # dimension attachment coincides with it; otherwise add a dedicated anchor.
    def add_dimension_anchor(geometry_index, coord, distance, anchor_kind="DIMENSION_ATTACH"):
        for existing_index, (owner, existing_coord) in enumerate(zip(anchor_owner, anchor_coords)):
            if owner == geometry_index and math.hypot(
                coord[0] - existing_coord[0], coord[1] - existing_coord[1]
            ) <= 1e-6:
                return existing_index
        idx = len(anchor_rows)
        center = geometry_centers[geometry_index]
        anchor_rows.append(_anchor_feature(
            coord, anchor_kind, (0.0, 0.0), 0.0,
            scale_safe, origin, center
        ))
        anchor_owner.append(geometry_index)
        anchor_coords.append(coord)
        anchor_kinds.append(anchor_kind)
        anchor_tangents.append((0.0, 0.0))
        _add_edge(
            edge_store, ("geometry", "has_anchor", "anchor"),
            geometry_index, idx, [distance / scale_safe, 1.0],
        )
        return idx

    # Add shared intersection anchors to both participating geometries.
    # These are distinct graph nodes so message passing can learn which
    # geometric junctions are meaningful in the engineering drawing.
    for gi, element_a in enumerate(geometry_elements):
        ga = _get(element_a, "geometry_2d")
        if ga is None or ga.is_empty:
            continue
        for gj in candidate_geometry_indices(ga, spatial_tolerance):
            if gj <= gi:
                continue
            gb = _get(geometry_elements[gj], "geometry_2d")
            if gb is None or gb.is_empty:
                continue
            try:
                if not ga.intersects(gb):
                    continue
                intersection = ga.intersection(gb)
            except Exception:
                continue
            for coord in _intersection_point_coords(intersection):
                for owner in (gi, gj):
                    anchor_idx = len(anchor_rows)
                    center = geometry_centers[owner]
                    anchor_rows.append(_anchor_feature(
                        coord, "INTERSECTION", (0.0, 0.0), 0.0,
                        scale_safe, origin, center
                    ))
                    anchor_owner.append(owner)
                    anchor_coords.append(coord)
                    anchor_kinds.append("INTERSECTION")
                    anchor_tangents.append((0.0, 0.0))
                    _add_edge(
                        edge_store, ("geometry", "has_anchor", "anchor"),
                        owner, anchor_idx, [0.0, 1.0],
                    )

    data["anchor"].x = feature_tensor(anchor_rows, 12)
    data["anchor"].element_id = [
        f"{data['geometry'].source_handle[owner]}:A{index}"
        for index, owner in enumerate(anchor_owner)
    ]
    data["anchor"].source_handle = [
        str(data["geometry"].source_handle[owner]) for owner in anchor_owner
    ]
    data["anchor"].source_layer = [
        str(data["geometry"].source_layer[owner]) for owner in anchor_owner
    ]
    data["anchor"].owner_geometry_index = list(anchor_owner)
    data["anchor"].anchor_kind = list(anchor_kinds)
    data["anchor"].coordinates = [tuple(coord) for coord in anchor_coords]

    # Keep the original broad dimension->geometry "describes" candidates.
    # Add more specific measurement roles based on the two definition points.
    for di, dimension in enumerate(dimension_elements):
        dim_type = str(_get(dimension, "dimension_type", "UNKNOWN")).upper()
        endpoints = _get(dimension, "endpoints") or []
        definition_points = _get(dimension, "definition_points") or []
        attachment_points = []

        # Special dimension semantics must precede generic measured points.
        if dim_type in {"RADIUS", "DIAMETRIC"}:
            center = _xy(_get(dimension, "center"))
            measure = _xy(_get(dimension, "measurement_point"))
            if center is None and len(endpoints) >= 2:
                center = _xy(endpoints[0])
            if measure is None and len(endpoints) >= 2:
                measure = _xy(endpoints[-1])
            if center:
                attachment_points.append(("measures_from", center, "CENTER"))
            if measure:
                attachment_points.append(("measures_to", measure, None))
            elif endpoints:
                p = _xy(endpoints[-1])
                if p:
                    attachment_points.append(("measures_to", p, None))
        elif dim_type in {"ANGULAR", "ANGULAR_3P"}:
            points = definition_points or endpoints
            for role, point in zip(("measures_from", "measures_to"), points[:2]):
                coord = _xy(point)
                if coord:
                    attachment_points.append((role, coord, None))
        else:
            # Definition points identify measured geometry; endpoints retain
            # the dimension arrow-line direction as an independent feature.
            measured_points = definition_points if len(definition_points) >= 2 else endpoints
            if len(measured_points) >= 2:
                attachment_points = [
                    ("measures_from", _xy(measured_points[0]), None),
                    ("measures_to", _xy(measured_points[1]), None),
                ]

        # Existing describes relation: nearest geometries to dimension
        # endpoints/center, bounded by dimension_tolerance.
        query_points = [Point(p) for _, p, _ in attachment_points if p is not None]
        if not query_points:
            center = _xy(_get(dimension, "center"))
            if center:
                query_points = [Point(center)]
        candidates = []
        candidate_indices = set()
        for query_point in query_points:
            candidate_indices.update(
                candidate_geometry_indices(query_point, dimension_tolerance)
            )
        for gi in sorted(candidate_indices):
            element = geometry_elements[gi]
            geom = _get(element, "geometry_2d")
            if geom is None or geom.is_empty or not query_points:
                continue
            dist = min(float(p.distance(geom)) for p in query_points)
            if dist <= dimension_tolerance:
                candidates.append((dist, gi))
        for dist, gi in sorted(candidates)[:max_neighbors]:
            element = geometry_elements[gi]
            _add_edge(
                edge_store, ("dimension", "describes", "geometry"),
                di, gi,
                dimension_geometry_attrs(dist, dimension, element),
            )

        # Role-specific association: each dimension definition point is
        # projected onto its nearest geometry and linked to a geometry anchor.
        # Radial center points attach to the geometry's center, not its boundary.
        for role, coord, requested_anchor_kind in attachment_points:
            if coord is None:
                continue
            point = Point(coord)
            best = None
            candidate_indices = (
                range(len(geometry_elements))
                if requested_anchor_kind == "CENTER"
                else candidate_geometry_indices(point, dimension_tolerance)
            )
            for gi in candidate_indices:
                element = geometry_elements[gi]
                geom = _get(element, "geometry_2d")
                if geom is None or geom.is_empty:
                    continue
                try:
                    if requested_anchor_kind == "CENTER":
                        if dim_type in {"RADIUS", "DIAMETRIC"}:
                            entity_type = str(_get(_get(element, "source"), "entity_type", "")).upper()
                            if entity_type not in {"CIRCLE", "ARC"}:
                                continue
                        element_center = _xy(_get(element, "center"))
                        if element_center is None:
                            centroid = geom.centroid
                            element_center = (float(centroid.x), float(centroid.y))
                        projected_coord = element_center
                        dist = math.hypot(coord[0] - element_center[0], coord[1] - element_center[1])
                    else:
                        projected = nearest_points(point, geom)[1]
                        projected_coord = (float(projected.x), float(projected.y))
                        dist = float(point.distance(projected))
                except Exception:
                    continue
                if dist <= dimension_tolerance and (best is None or dist < best[0]):
                    best = (dist, gi, projected_coord)
            if best is None:
                continue
            dist, gi, projected_coord = best
            anchor_idx = add_dimension_anchor(
                gi, projected_coord, dist,
                anchor_kind=requested_anchor_kind or "DIMENSION_ATTACH",
            )
            _add_edge(
                edge_store, ("dimension", role, "anchor"),
                di, anchor_idx,
                [dist / scale_safe, max(0.0, 1.0 - dist / max(dimension_tolerance, 1e-9))],
            )
            _add_edge(
                edge_store, ("anchor", "rev_" + role, "dimension"),
                anchor_idx, di,
                [dist / scale_safe, max(0.0, 1.0 - dist / max(dimension_tolerance, 1e-9))],
            )
            _add_edge(
                edge_store, ("dimension", role, "geometry"),
                di, gi,
                dimension_geometry_attrs(dist, dimension, element),
            )
            _add_edge(
                edge_store, ("geometry", "rev_" + role, "dimension"),
                gi, di,
                [dist / scale_safe, max(0.0, 1.0 - dist / max(dimension_tolerance, 1e-9))],
            )

    # Rebuild anchor tensors after dimension-attachment anchors were appended.
    data["anchor"].x = feature_tensor(anchor_rows, 12)
    data["anchor"].element_id = [
        f"{data['geometry'].source_handle[owner]}:A{index}"
        for index, owner in enumerate(anchor_owner)
    ]
    data["anchor"].source_handle = [
        str(data["geometry"].source_handle[owner]) for owner in anchor_owner
    ]
    data["anchor"].source_layer = [
        str(data["geometry"].source_layer[owner]) for owner in anchor_owner
    ]
    data["anchor"].owner_geometry_index = list(anchor_owner)
    data["anchor"].anchor_kind = list(anchor_kinds)
    data["anchor"].coordinates = [tuple(coord) for coord in anchor_coords]

    # Reverse ownership edges are materialized in the common reverse-edge pass.

    # --------------------------------------------------------------
    # Text -> geometry semantic candidates (v8).
    # Pure annotation-only text remains node-only; mixed text may still emit
    # candidates for its measurement/part/geometry-description categories.
    # --------------------------------------------------------------
    # Collect the existing Dimension -> Geometry evidence so that a text
    # diameter/radius callout can be checked against a dimension already
    # attached through its measured points/anchors.
    dimension_evidence_by_geometry = defaultdict(list)
    for relation_name in ("describes", "measures_from", "measures_to"):
        relation_type = ("dimension", relation_name, "geometry")
        for dimension_index, geometry_index, edge_attrs in edge_store.get(relation_type, []):
            dimension = dimension_elements[dimension_index]
            kind = str(_get(dimension, "dimension_type", "UNKNOWN")).upper()
            displayed = _get(dimension, "length")
            actual = _get(dimension, "actual_length")
            try:
                value = float(displayed)
                value_valid = math.isfinite(value)
            except (TypeError, ValueError, OverflowError):
                try:
                    value = float(actual)
                    value_valid = math.isfinite(value)
                except (TypeError, ValueError, OverflowError):
                    value, value_valid = 0.0, False
            dimension_evidence_by_geometry[geometry_index].append({
                "kind": kind,
                "value": value if value_valid else 0.0,
                "value_valid": value_valid,
                "distance": _safe_float(edge_attrs[0]) * scale_safe if edge_attrs else float("inf"),
            })

    text_semantics, text_semantic_categories = [], []
    text_centers, text_bounds, text_measurements = [], [], []
    for text in text_elements:
        categories, normalized = classify_text_categories(
            _get(text, "text", ""), text_config
        )
        category = categories[0]
        text_semantics.append(category)
        text_semantic_categories.append(list(categories))
        evidence = parse_measurement_evidence(normalized, text_config)
        bound = _get(text, "bound") or _get(text, "bound_moved")
        center = _xy(_get(text, "position")) or _xy(_get(text, "position_moved"))
        if center is None and bound is not None and not bound.is_empty:
            c = bound.centroid
            center = (float(c.x), float(c.y))
        center = center or (0.0, 0.0)
        if bound is None or getattr(bound, "is_empty", True):
            bound = Point(center)
        text_centers.append(center)
        text_bounds.append(bound)
        text_measurements.append(evidence)

    geometry_centers_for_text = []
    for element in geometry_elements:
        geom = _get(element, "geometry_2d")
        if geom is None or geom.is_empty:
            geometry_centers_for_text.append(None)
            continue
        center = _xy(_get(element, "center"))
        if center is None:
            c = geom.centroid
            center = (float(c.x), float(c.y))
        geometry_centers_for_text.append(center)

    data["text"].content = [str(_get(t, "text", "") or "") for t in text_elements]
    data["text"].semantic_type = list(text_semantics)
    data["text"].semantic_types = [list(values) for values in text_semantic_categories]
    data["text"].normalized_content = [normalize_text(_get(t, "text", ""), text_config) for t in text_elements]
    data["text"].has_diameter_symbol = [bool(x["has_diameter_symbol"]) for x in text_measurements]
    data["text"].diameter_value = [
        float(x["diameter_value"]) if x["diameter_value"] is not None else float("nan")
        for x in text_measurements
    ]
    data["text"].has_radius_symbol = [bool(x["has_radius_symbol"]) for x in text_measurements]
    data["text"].radius_value = [
        float(x["radius_value"]) if x["radius_value"] is not None else float("nan")
        for x in text_measurements
    ]

    compatibility = text_config.get("semantic_compatibility", {})
    geometry_type_compatibility = text_config.get(
        "semantic_compatibility_geometry_types", {}
    )
    ranking = text_config.get("candidate_ranking", {})
    bbox_weight = float(ranking.get("bbox_distance_weight", 0.40))
    center_weight = float(ranking.get("text_center_to_geometry_weight", 0.35))
    centroid_weight = float(ranking.get("text_center_to_geometry_center_weight", 0.25))
    weight_sum = max(bbox_weight + center_weight + centroid_weight, 1e-9)
    bbox_weight, center_weight, centroid_weight = (
        bbox_weight / weight_sum, center_weight / weight_sum,
        centroid_weight / weight_sum,
    )
    spatial_rank_weight = float(ranking.get("spatial_rank_weight", 0.65))
    semantic_rank_weight = float(ranking.get("semantic_rank_weight", 0.35))
    rank_weight_sum = max(spatial_rank_weight + semantic_rank_weight, 1e-9)
    spatial_rank_weight /= rank_weight_sum
    semantic_rank_weight /= rank_weight_sum
    maximum_spatial_rank = max(
        0.0, float(ranking.get("maximum_spatial_rank", 1.25))
    )

    relation_by_category = {
        "DIMENSION_VALUE": "dimension_value_candidate",
        "PART_LABEL": "part_label_candidate",
        "GEOMETRY_DESCRIPTION": "geometry_description_candidate",
        "TOLERANCE_GDT": "gdt_candidate",
    }
    for ti, text in enumerate(text_elements):
        for category in text_semantic_categories[ti]:
            relation = relation_by_category.get(category)
            if relation is None:
                # In particular, ANNOTATION is intentionally excluded here.
                continue
            query, text_center = text_bounds[ti], text_centers[ti]
            measurement = text_measurements[ti]
            candidates = []
            for gi in candidate_geometry_indices(query, text_candidate_search_tolerance):
                element = geometry_elements[gi]
                geom = _get(element, "geometry_2d")
                if geom is None or geom.is_empty:
                    continue
    
                # Keep all three independent distances. A zero bounding-box gap
                # must not hide a text-center or geometry-center mismatch.
                bbox_distance = float(query.distance(geom.envelope))
                text_center_distance = float(Point(text_center).distance(geom))
                geom_center = geometry_centers_for_text[gi]
                center_distance = (
                    math.hypot(
                        text_center[0] - geom_center[0],
                        text_center[1] - geom_center[1],
                    ) if geom_center is not None else float("inf")
                )
                bbox_norm = min(bbox_distance / max(text_candidate_search_tolerance, 1e-9), 2.0)
                center_norm = min(text_center_distance / max(text_candidate_search_tolerance, 1e-9), 2.0)
                centroid_norm = (
                    min(center_distance / max(text_candidate_search_tolerance, 1e-9), 2.0)
                    if math.isfinite(center_distance) else 2.0
                )
                spatial_rank = (
                    bbox_weight * bbox_norm
                    + center_weight * center_norm
                    + centroid_weight * centroid_norm
                )
                if spatial_rank > maximum_spatial_rank:
                    continue
                combined_distance = spatial_rank * max(float(text_candidate_search_tolerance), 1e-9)
                proximity = max(
                    0.0, 1.0 - spatial_rank / max(maximum_spatial_rank, 1e-9)
                )
    
                entity_type = str(
                    _get(_get(element, "source"), "entity_type", "OTHER")
                ).upper()
                geometry_type = str(_get(element, "geometry_type", "OTHER")).upper()
                allowed_entities = {
                    str(v).upper() for v in compatibility.get(category, [])
                }
                allowed_geometry_types = {
                    str(v).upper()
                    for v in geometry_type_compatibility.get(category, [])
                }
                entity_compatible = entity_type in allowed_entities if allowed_entities else True
                shape_compatible = (
                    geometry_type in allowed_geometry_types
                    if allowed_geometry_types else True
                )
                semantic_score = (
                    1.0 if entity_compatible and shape_compatible
                    else 0.65 if entity_compatible or shape_compatible
                    else 0.25
                )
                if category == "DIMENSION_VALUE" and (
                    measurement["has_diameter_symbol"] or measurement["has_radius_symbol"]
                ):
                    circular_entity = entity_type in {"CIRCLE", "ARC", "ELLIPSE"}
                    closed_profile = bool(_get(element, "is_closed", False))
                    semantic_score = (
                        1.0 if circular_entity or closed_profile else 0.05
                    )
    
                diameter_value = measurement["diameter_value"]
                radius_value = measurement["radius_value"]
                geom_bounds = _bounds(geom)
                span_x, span_y = (
                    (geom_bounds[2] - geom_bounds[0], geom_bounds[3] - geom_bounds[1])
                    if geom_bounds else (0.0, 0.0)
                )
                geom_span = max(span_x, span_y)
                diameter_fit = (
                    abs(diameter_value - geom_span)
                    / max(abs(diameter_value), abs(geom_span), 1e-9)
                    if diameter_value is not None else 0.0
                )
                radius_fit = (
                    abs(2.0 * radius_value - geom_span)
                    / max(2.0 * abs(radius_value), abs(geom_span), 1e-9)
                    if radius_value is not None else 0.0
                )
    
                # Compare text values with actual linked dimension semantics.
                # DIAMETRIC dimensions carry diameter values; RADIUS dimensions
                # carry radius values. This is additional evidence, not a hard
                # engineering constraint or an automatically confirmed match.
                linked_dimensions = dimension_evidence_by_geometry.get(gi, [])
                best_dimension = None
                best_dimension_score = -1.0
                for dim_evidence in linked_dimensions:
                    kind = dim_evidence["kind"]
                    dim_value = dim_evidence["value"]
                    dim_valid = dim_evidence["value_valid"]
                    expected_text_value = (
                        diameter_value if measurement["has_diameter_symbol"]
                        else radius_value if measurement["has_radius_symbol"]
                        else None
                    )
                    kind_compatible = (
                        measurement["has_diameter_symbol"] and kind == "DIAMETRIC"
                    ) or (
                        measurement["has_radius_symbol"] and kind == "RADIUS"
                    )
                    if expected_text_value is not None and dim_valid:
                        agreement = math.exp(
                            -abs(dim_value - expected_text_value)
                            / max(abs(dim_value), abs(expected_text_value), scale_safe * 0.01, 1e-9)
                        )
                    else:
                        agreement = 0.0
                    score = (
                        (1.0 if kind_compatible else 0.0) * 0.55
                        + agreement * 0.35
                        + (1.0 if dim_valid else 0.0) * 0.05
                        + math.exp(-dim_evidence["distance"] / max(dimension_tolerance, 1e-9)) * 0.05
                    )
                    if score > best_dimension_score:
                        best_dimension_score = score
                        best_dimension = (dim_evidence, kind_compatible, agreement)
    
                if best_dimension is None:
                    has_dim_diametric = has_dim_radius = dim_value_valid = 0.0
                    dim_value_norm = dim_agreement = dim_distance_norm = 0.0
                    has_dimension_evidence = has_compatible_dimension = 0.0
                else:
                    dim_evidence, kind_compatible, agreement = best_dimension
                    has_dim_diametric = float(dim_evidence["kind"] == "DIAMETRIC")
                    has_dim_radius = float(dim_evidence["kind"] == "RADIUS")
                    dim_value_valid = float(dim_evidence["value_valid"])
                    dim_value_norm = dim_evidence["value"] / scale_safe if dim_evidence["value_valid"] else 0.0
                    dim_agreement = agreement
                    dim_distance_norm = dim_evidence["distance"] / scale_safe
                    has_dimension_evidence = 1.0
                    has_compatible_dimension = float(kind_compatible)
    
                geometry_type_vector = [
                    1.0 if geometry_type == item else 0.0
                    for item in GEOMETRY_TYPES
                ]
                entity_type_vector = [
                    float(entity_type == "CIRCLE"),
                    float(entity_type == "ARC"),
                    float(entity_type == "ELLIPSE"),
                ]
                aspect_ratio = min(
                    span_x, span_y
                ) / max(max(span_x, span_y), 1e-9)
                # Do not expose an area-derived circularity statistic as an input:
                # it can leak the area target. Use a bbox-only shape proxy instead.
                bbox_shape_proxy = aspect_ratio
    
                edge_attrs = [
                    bbox_distance / scale_safe,
                    text_center_distance / scale_safe,
                    center_distance / scale_safe if math.isfinite(center_distance) else 0.0,
                    combined_distance / scale_safe,
                    proximity, semantic_score,
                    float(measurement["has_diameter_symbol"]),
                    float(measurement["has_radius_symbol"]),
                    float(diameter_value is not None),
                    float(diameter_value or 0.0) / scale_safe,
                    float(radius_value is not None),
                    float(radius_value or 0.0) / scale_safe,
                    float(entity_type in {"CIRCLE", "ARC"}),
                    float(bool(_get(element, "is_closed", False))),
                    diameter_fit, radius_fit,
                    *geometry_type_vector,
                    *entity_type_vector,
                    aspect_ratio,
                    geom_span / scale_safe,
                    bbox_shape_proxy,
                    has_dim_diametric,
                    has_dim_radius,
                    dim_value_valid,
                    dim_value_norm,
                    dim_agreement,
                    dim_distance_norm,
                    has_dimension_evidence,
                    has_compatible_dimension,
                    0.0,  # reviewed_pair_override
                ]
                combined_rank = (
                    spatial_rank_weight * spatial_rank
                    + semantic_rank_weight * (1.0 - semantic_score)
                )
                candidates.append(
                    (combined_rank, combined_distance, -semantic_score, gi, edge_attrs)
                )
    
            # Semantic compatibility is applied before top-k truncation. A
            # semantically suitable circle/closed profile can outrank a nearer
            # but incompatible line or annotation-like shape.
            candidates.sort(key=lambda item: (item[0], item[1], item[2]))
            for _, _, _, gi, edge_attrs in candidates[:max_neighbors]:
                _add_edge(
                    edge_store, ("text", relation, "geometry"), ti, gi, edge_attrs
                )
    # --------------------------------------------------------------
    # Text -> dimension candidates. This gives dimension values and GD&T
    # a path into the existing Dimension -> Anchor -> Geometry evidence.
    # --------------------------------------------------------------
    for ti, text in enumerate(text_elements):
        categories = set(text_semantic_categories[ti])
        if not categories.intersection({
            "DIMENSION_VALUE", "TOLERANCE_GDT", "PART_LABEL", "GEOMETRY_DESCRIPTION"
        }):
            # Pure general notes remain node-only unless reviewed explicitly.
            continue
        query = text_bounds[ti]
        matches = []
        for di, dimension in enumerate(dimension_elements):
            endpoints = _get(dimension, "endpoints") or []
            p1 = _xy(endpoints[0]) if len(endpoints) >= 2 else None
            p2 = _xy(endpoints[1]) if len(endpoints) >= 2 else None
            center = _xy(_get(dimension, "center"))
            try:
                reference = LineString([p1, p2]) if p1 and p2 else (Point(center) if center else None)
                if reference is None:
                    continue
                distance = float(query.distance(reference))
            except Exception:
                continue
            if distance <= dimension_tolerance:
                dim_type = str(_get(dimension, "dimension_type", "UNKNOWN")).upper()
                if "DIMENSION_VALUE" in categories:
                    semantic_score = 1.0 if dim_type in {"LINEAR", "ALIGNED", "DIAMETRIC", "RADIUS"} else 0.25
                elif "TOLERANCE_GDT" in categories:
                    semantic_score = 1.0 if dim_type in {"ANGULAR", "ANGULAR_3P", "DIAMETRIC", "RADIUS"} else 0.4
                else:
                    semantic_score = 0.7
                matches.append((distance, -semantic_score, di, semantic_score))
        for distance, _, di, semantic_score in sorted(matches)[:max_neighbors]:
            evidence = text_measurements[ti]
            confidence = max(0.0, 1.0 - distance / max(float(dimension_tolerance), 1e-9))
            attrs = [
                distance / scale_safe, confidence, semantic_score,
                float(evidence["has_diameter_symbol"]),
                float(evidence["has_radius_symbol"]),
                float(evidence["diameter_value"] is not None),
                float(evidence["diameter_value"] or 0.0) / scale_safe,
                float(evidence["radius_value"] is not None),
                float(evidence["radius_value"] or 0.0) / scale_safe,
            ]
            _add_edge(edge_store, ("text", "labels", "dimension"), ti, di, attrs)

    # --------------------------------------------------------------
    # Dimension-to-dimension relationships
    # --------------------------------------------------------------
    # These are candidate relationships, not ground-truth constraints.
    # They let the GNN reason over dimension chains, parallel dimension
    # lines, and dimensions sharing a measurement axis.
    def _dimension_descriptor(item):
        endpoints = _get(item, "endpoints")
        p1 = _xy(endpoints[0]) if endpoints and len(endpoints) >= 2 else None
        p2 = _xy(endpoints[1]) if endpoints and len(endpoints) >= 2 else None
        center = _xy(_get(item, "center"))
        if center is None and p1 and p2:
            center = ((p1[0] + p2[0]) * 0.5, (p1[1] + p2[1]) * 0.5)
        direction = None
        if p1 and p2:
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            length = math.hypot(dx, dy)
            if length > 1e-9:
                direction = (dx / length, dy / length)
        return center, direction, p1, p2

    dimension_descriptors = [
        _dimension_descriptor(item) for item in dimension_elements
    ]
    cell_size = max(float(dimension_tolerance), float(connection_tolerance), 1e-6)
    dimension_buckets = defaultdict(list)
    for di, descriptor in enumerate(dimension_descriptors):
        center = descriptor[0]
        if center is not None:
            cell = (math.floor(center[0] / cell_size), math.floor(center[1] / cell_size))
            dimension_buckets[cell].append(di)

    dimension_pairs = set()
    for di, (center_a, direction_a, p1a, p2a) in enumerate(dimension_descriptors):
        if center_a is None:
            continue
        cell_x = math.floor(center_a[0] / cell_size)
        cell_y = math.floor(center_a[1] / cell_size)
        nearby_indices = set()
        for dx_cell in (-1, 0, 1):
            for dy_cell in (-1, 0, 1):
                nearby_indices.update(dimension_buckets.get(
                    (cell_x + dx_cell, cell_y + dy_cell), ()
                ))
        scored = []
        for dj in nearby_indices:
            if dj <= di:
                continue
            center_b, direction_b, p1b, p2b = dimension_descriptors[dj]
            if center_b is None:
                continue
            center_distance = math.hypot(
                center_a[0] - center_b[0], center_a[1] - center_b[1]
            )
            if center_distance > dimension_tolerance:
                continue
            angle = _angle_between(direction_a, direction_b)
            endpoint_gap = min(
                (math.hypot(a[0] - b[0], a[1] - b[1])
                 for a in (p1a, p2a) if a is not None
                 for b in (p1b, p2b) if b is not None),
                default=float("inf"),
            )
            axis_gap = 0.0
            if direction_a is not None:
                axis_gap = abs(
                    (center_b[0] - center_a[0]) * direction_a[1]
                    - (center_b[1] - center_a[1]) * direction_a[0]
                )
            scored.append((center_distance, dj, angle, endpoint_gap, axis_gap))
        for center_distance, dj, angle, endpoint_gap, axis_gap in sorted(scored)[:max_neighbors]:
            normalized_distance = center_distance / scale_safe
            confidence = max(
                0.0,
                1.0 - center_distance / max(float(dimension_tolerance), 1e-9),
            )
            attrs = [
                normalized_distance,
                (angle / math.pi) if angle is not None else 0.0,
                (endpoint_gap / scale_safe) if math.isfinite(endpoint_gap) else 0.0,
                axis_gap / scale_safe,
                confidence,
            ]
            _add_edge(
                edge_store, ("dimension", "near", "dimension"), di, dj, attrs
            )
            if angle is not None and angle <= angular_tol:
                _add_edge(
                    edge_store, ("dimension", "parallel", "dimension"),
                    di, dj, attrs,
                )
                if axis_gap <= max(connection_tolerance, 1e-9):
                    _add_edge(
                        edge_store, ("dimension", "same_axis", "dimension"),
                        di, dj, attrs,
                    )
            if endpoint_gap <= max(connection_tolerance, 0.0):
                _add_edge(
                    edge_store, ("dimension", "chain_candidate", "dimension"),
                    di, dj, attrs,
                )

    # Keep a stable relation schema across drawings, including relations with
    # zero edges in a particular drawing. This is essential when training a
    # single model over separate train/validation/test drawings.
    canonical_edge_dims = {
        ("geometry", "near", "geometry"): 10,
        ("geometry", "parallel", "geometry"): 10,
        ("geometry", "perpendicular", "geometry"): 10,
        ("geometry", "intersects", "geometry"): 10,
        ("geometry", "touches", "geometry"): 10,
        ("geometry", "overlaps", "geometry"): 10,
        ("geometry", "contains", "geometry"): 10,
        ("geometry", "within", "geometry"): 10,
        ("geometry", "connected", "geometry"): 10,
        ("geometry", "collinear", "geometry"): 10,
        ("geometry", "equal_length_candidate", "geometry"): 3,
        ("geometry", "mirror_candidate", "geometry"): 5,
        ("geometry", "has_anchor", "anchor"): 2,
        ("dimension", "describes", "geometry"): 12,
        ("dimension", "measures_from", "geometry"): 12,
        ("dimension", "measures_to", "geometry"): 12,
        ("dimension", "measures_from", "anchor"): 2,
        ("dimension", "measures_to", "anchor"): 2,
        ("text", "describes", "geometry"): 2,
        ("text", "dimension_value_candidate", "geometry"): 39,
        ("text", "part_label_candidate", "geometry"): 39,
        ("text", "geometry_description_candidate", "geometry"): 39,
        ("text", "gdt_candidate", "geometry"): 39,
        ("text", "reviewed_match_candidate", "geometry"): 39,
        ("text", "labels", "dimension"): 9,
        ("dimension", "near", "dimension"): 5,
        ("dimension", "parallel", "dimension"): 5,
        ("dimension", "same_axis", "dimension"): 5,
        ("dimension", "chain_candidate", "dimension"): 5,
    }
    for forward_type, width in canonical_edge_dims.items():
        edge_store[forward_type]  # ensure the canonical store exists


    # Materialize reverse relations in the store first. This also handles
    # explicitly authored role-reverse edges without accidentally dropping
    # both directions during tensor installation.
    for edge_type, records in list(edge_store.items()):
        if edge_type[1].startswith("rev_"):
            continue
        reverse_type = (edge_type[2], "rev_" + edge_type[1], edge_type[0])
        if reverse_type not in edge_store or not edge_store[reverse_type]:
            edge_store[reverse_type] = [
                (dst, src, list(attrs)) for src, dst, attrs in records
            ]

    # Install edge_index and edge_attr. Empty relations are materialized too,
    # keeping a stable schema across separate drawing graphs.
    for edge_type, records in list(edge_store.items()):
        if not records:
            width = canonical_edge_dims.get(
                edge_type,
                canonical_edge_dims.get(
                    (edge_type[2], edge_type[1].removeprefix("rev_"), edge_type[0]), 2
                ),
            )
            data[edge_type].edge_index = torch.empty((2, 0), dtype=torch.long)
            data[edge_type].edge_attr = torch.empty((0, int(width)), dtype=torch.float)
            continue
        src = torch.tensor([[r[0] for r in records], [r[1] for r in records]], dtype=torch.long)
        widths = {len(r[2]) for r in records}
        if len(widths) != 1:
            raise ValueError(f"Inconsistent edge feature widths for {edge_type}: {widths}")
        attr = torch.tensor([r[2] for r in records], dtype=torch.float)
        data[edge_type].edge_index = src
        data[edge_type].edge_attr = attr

    data.graph_metadata = {
        "graph_type": "dxf_semantic_heterogeneous",
        "feature_version": 8,
        "measurement_derivation_schema": "circle_arc_length_from_predicted_radius_v1",
        "geometry_feature_schema": "dxf_geometry_shape_v8",
        "geometry_feature_names": list(GEOMETRY_FEATURE_NAMES),
        "geometry_feature_dimension": 24 + len(GEOMETRY_FEATURE_NAMES),
        "text_semantics_config": str(text_config_path or "text_semantics.json"),
        "text_semantics_config_version": int(text_config.get("version", 1)),
        "text_candidate_ranking": ranking,
        "text_feature_categories": list(TEXT_CATEGORIES),
        "text_feature_schema": list(TEXT_FEATURE_NAMES),
        "text_semantics_categories": {
            category: int(sum(value == category for value in text_semantics))
            for category in sorted(set(text_semantics))
        },
        "text_semantics_multi_label_counts": {
            category: int(sum(category in values for values in text_semantic_categories))
            for category in TEXT_CATEGORIES
        },
        "text_geometry_edge_features": [
            "bbox_distance", "text_center_to_geometry_distance",
            "text_center_to_geometry_center_distance", "weighted_spatial_distance",
            "proximity", "semantic_compatibility", "has_diameter_symbol",
            "has_radius_symbol", "diameter_value_valid", "diameter_value",
            "radius_value_valid", "radius_value", "geometry_is_circle_or_arc",
            "geometry_is_closed", "diameter_to_geometry_bbox_relative_error",
            "radius_to_geometry_bbox_relative_error",
            "geometry_type_closed_profile", "geometry_type_linear_geometry",
            "geometry_type_point", "geometry_type_other", "geometry_type_unknown",
            "geometry_type_polygon", "geometry_type_linestring",
            "geometry_type_multilinestring", "entity_type_circle", "entity_type_arc",
            "entity_type_ellipse", "geometry_bbox_aspect_ratio",
            "geometry_bbox_max_span", "bbox_shape_proxy_no_area_leak",
            "linked_diametric_dimension", "linked_radius_dimension",
            "linked_dimension_value_valid", "linked_dimension_value",
            "text_dimension_value_agreement", "linked_dimension_distance",
            "has_linked_dimension", "has_semantically_compatible_dimension",
            "reviewed_pair_override",
        ],
        "dimension_geometry_edge_features": [
            "normalized_distance", "proximity", "is_diametric", "is_radius",
            "is_linear", "is_angular", "display_value_valid",
            "normalized_display_value", "actual_value_valid",
            "normalized_actual_value", "geometry_is_circle_or_arc",
            "geometry_is_closed",
        ],
        "anchor_features": [
            "normalized_x", "normalized_y", "anchor_kind_one_hot",
            "local_tangent_x", "local_tangent_y", "signed_local_curvature",
            "distance_to_geometry_center",
        ],
        "mirror_candidate_features": [
            "normalized_reflection_error", "axis_angle_over_180",
            "normalized_axis_midpoint_x", "normalized_axis_midpoint_y",
            "mirror_confidence",
        ],
        "mirror_axis_search": {
            "coarse_step_degrees": 5.0,
            "refinement_step_degrees": 1.0,
            "range_degrees": 180.0,
        },
        "text_annotation_policy": "All semantic categories are encoded in text node features; annotation nodes remain non-linking unless reviewed positive labels add an edge.",
        "spatial_tolerance": float(spatial_tolerance),
        "relation_search_tolerance": float(relation_search_tolerance),
        "global_relation_max_neighbors": int(global_relation_max_neighbors),
        "text_tolerance": float(text_tolerance),
        "text_candidate_search_tolerance": float(text_candidate_search_tolerance),
        "dimension_tolerance": float(dimension_tolerance),
        "connection_tolerance": float(connection_tolerance),
        "collinear_tolerance": float(collinear_tolerance),
        "tangent_tolerance_degrees": float(tangent_tolerance_degrees),
        "curvature_tolerance": float(curvature_tolerance),
        "mirror_tolerance": float(mirror_tolerance),
        "origin": origin,
        "scale": float(scale_safe),
        "node_counts": {
            "geometry": gcount,
            "dimension": dcount,
            "text": tcount,
            "anchor": len(anchor_rows),
        },
        "feature_dims": {
            "geometry": 24 + len(GEOMETRY_FEATURE_NAMES),
            "dimension": 17,
            "text": len(TEXT_FEATURE_NAMES),
            "anchor": 12,
        },
        "geometry_relation_edge_attr": [
            "normalized_distance",
            "normalized_angle_difference",
            "normalized_intersection_length",
            "normalized_endpoint_distance",
            "overlap_ratio",
            "confidence",
            "endpoint_distance_valid",
            "tangent_continuity",
            "curvature_similarity",
            "collinear_score",
        ],
        "edge_feature_dims": {
            "|".join(edge_type): int(data[edge_type].edge_attr.size(-1))
            for edge_type in data.edge_types
        },
        "measurement_learning": {
            "learned_targets": ["length_non_circle_arc", "radius"],
            "derived_targets": ["circle_arc_length", "area"],
            "circle_length": "2*pi*predicted_radius",
            "arc_length": "predicted_radius*arc_sweep_angle_rad",
            "arc_sweep_angle_source": "DXF start/end angles in degrees when available; otherwise ordered geometry path",
            "analytic_length_area_used_as_input": False,
            "area_prediction": "CIRCLE: pi*predicted_radius^2; other closed shapes: raw_area*(predicted_length/raw_perimeter)^2",
            "radius_input_feature": False,
            "radius_target_source": "raw_dxf_entity_radius",
            "radius_measured_is_separate": True,
            "area_validity": "closed CIRCLE or closed shape with positive raw Shapely area/perimeter",
            "raw_geometry_shape_metadata_used_for_area_derivation": True,
            "radius_validity": "entity_type in {CIRCLE, ARC}",
            "target_encoding": "log1p",
        },
        "edge_counts": {
            str(edge_type): int(data[edge_type].edge_index.size(1))
            for edge_type in data.edge_types
        },
    }
    return data


def build_semantic_graph_from_analysis(
    geometry_elements,
    dimension_elements,
    text_elements,
    raw_entities=None,
    analytic_graph=None,
    **kwargs,
):
    """Named adapter for pipeline/service code; accepts already-extracted objects."""
    return build_semantic_graph(
        geometry_elements=geometry_elements,
        dimension_elements=dimension_elements,
        text_elements=text_elements,
        raw_entities=raw_entities,
        analytic_graph=analytic_graph,
        **kwargs,
    )
