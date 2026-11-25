from __future__ import annotations

import math
from typing import Any

# v8 geometry descriptors. None of these stores the supervised analytic
# Length/Area target itself. In particular, area, fill-ratio, solidity and
# circularity are deliberately excluded because they can directly reveal
# the Area target for closed profiles.
GEOMETRY_FEATURE_VERSION = 8
GEOMETRY_FEATURE_NAMES = (
    "bbox_diagonal_over_scale",
    "bbox_aspect_ratio",
    "line_part_count_log",
    "geometry_component_count_log",
    "convex_hull_to_boundary_perimeter_ratio",
    "segment_count_log",
    "segment_mean_fraction_of_boundary",
    "segment_max_fraction_of_boundary",
    "segment_length_coefficient_of_variation",
    "principal_axis_major_over_scale",
    "principal_axis_minor_over_scale",
    "principal_axis_ratio",
    "hole_count_log",
    "hole_boundary_fraction",
    "holes_per_segment",
    "boundary_complexity_over_bbox_diagonal",
    "is_polygonal",
    "is_circle",
    "is_arc",
    "has_perimeter",
    "has_hole_data",
)


def _get(obj: Any, name: str, default=None):
    return obj.get(name, default) if isinstance(obj, dict) else getattr(obj, name, default)


def _safe(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except (TypeError, ValueError, OverflowError):
        return default


def _line_parts(geometry):
    if geometry is None or getattr(geometry, "is_empty", True):
        return []
    kind = getattr(geometry, "geom_type", "")
    if kind in {"LineString", "LinearRing"}:
        return [geometry]
    if kind in {"MultiLineString", "GeometryCollection"}:
        result = []
        for part in geometry.geoms:
            result.extend(_line_parts(part))
        return result
    if kind == "Polygon":
        return [geometry.exterior, *list(geometry.interiors)]
    if kind == "MultiPolygon":
        result = []
        for polygon in geometry.geoms:
            result.extend([polygon.exterior, *list(polygon.interiors)])
        return result
    return []


def _polygonal_view(geometry, is_closed: bool):
    if geometry is None or getattr(geometry, "is_empty", True):
        return None
    if geometry.geom_type in {"Polygon", "MultiPolygon"}:
        return geometry
    if is_closed and geometry.geom_type in {"LineString", "LinearRing"}:
        try:
            from shapely.geometry import Polygon
            candidate = Polygon(geometry)
            if candidate.is_valid and not candidate.is_empty:
                return candidate
        except Exception:
            pass
    return None


def _principal_axis_spans(parts):
    points = []
    for part in parts:
        try:
            points.extend(
                (float(p[0]), float(p[1]))
                for p in part.coords
                if math.isfinite(float(p[0])) and math.isfinite(float(p[1]))
            )
        except Exception:
            continue
    if len(points) < 2:
        return 0.0, 0.0
    mx = sum(p[0] for p in points) / len(points)
    my = sum(p[1] for p in points) / len(points)
    xx = sum((p[0] - mx) ** 2 for p in points) / len(points)
    yy = sum((p[1] - my) ** 2 for p in points) / len(points)
    xy = sum((p[0] - mx) * (p[1] - my) for p in points) / len(points)
    angle = 0.5 * math.atan2(2.0 * xy, xx - yy)
    c, s = math.cos(angle), math.sin(angle)
    projected = [
        ((x - mx) * c + (y - my) * s,
         -(x - mx) * s + (y - my) * c)
        for x, y in points
    ]
    major = max(p[0] for p in projected) - min(p[0] for p in projected)
    minor = max(p[1] for p in projected) - min(p[1] for p in projected)
    return max(0.0, major), max(0.0, minor)


def extract_geometry_descriptors(element, scale: float = 1.0) -> list[float]:
    """Return v8 shape descriptors with explicit availability indicators.

    Shape descriptors are recomputed from geometry_2d. The node vector deliberately
    excludes absolute perimeter, arc length, area, and radius values; it keeps
    dimensionless boundary/segment ratios, topology counts, normalized bounds,
    and principal-axis extents. No area-derived ratio is exposed to the model.
    """
    geometry = _get(element, "geometry_2d")
    scale = max(abs(_safe(scale, 1.0)), 1e-9)
    is_closed = bool(_get(element, "is_closed", False))
    entity_type = str(_get(_get(element, "source"), "entity_type", "")).upper()
    bounds = None
    if geometry is not None and not getattr(geometry, "is_empty", True):
        try:
            bounds = tuple(float(v) for v in geometry.bounds)
        except Exception:
            bounds = None

    if bounds and len(bounds) == 4 and all(math.isfinite(v) for v in bounds):
        minx, miny, maxx, maxy = bounds
        width, height = max(0.0, maxx - minx), max(0.0, maxy - miny)
        diagonal = math.hypot(width, height) / scale
        aspect = min(width, height) / max(width, height, 1e-9)
    else:
        diagonal = aspect = 0.0

    parts = _line_parts(geometry)
    segment_lengths = []
    for part in parts:
        try:
            coords = list(part.coords)
        except Exception:
            continue
        for a, b in zip(coords[:-1], coords[1:]):
            length = math.hypot(float(b[0]) - float(a[0]), float(b[1]) - float(a[1]))
            if math.isfinite(length) and length > 1e-9:
                segment_lengths.append(length / scale)

    perimeter_raw = _safe(getattr(geometry, "length", 0.0)) if geometry is not None else 0.0
    hull_perimeter_raw = 0.0
    if geometry is not None and not getattr(geometry, "is_empty", True):
        try:
            hull_perimeter_raw = _safe(geometry.convex_hull.length)
        except Exception:
            pass
    has_perimeter = perimeter_raw > 1e-9
    perimeter_scaled = perimeter_raw / scale if has_perimeter else 0.0

    hole_count = 0
    hole_perimeter_raw = 0.0
    has_hole_data = False
    polygonal = _polygonal_view(geometry, is_closed)
    if polygonal is not None:
        try:
            polygons = list(polygonal.geoms) if polygonal.geom_type == "MultiPolygon" else [polygonal]
            for polygon in polygons:
                hole_count += len(polygon.interiors)
                hole_perimeter_raw += sum(float(ring.length) for ring in polygon.interiors)
            has_hole_data = True
        except Exception:
            hole_count = 0
            hole_perimeter_raw = 0.0
            has_hole_data = False

    count = len(segment_lengths)
    mean_length = sum(segment_lengths) / count if count else 0.0
    max_length = max(segment_lengths, default=0.0)
    std_length = (
        math.sqrt(sum((v - mean_length) ** 2 for v in segment_lengths) / count)
        if count else 0.0
    )
    major, minor = _principal_axis_spans(parts)
    major /= scale
    minor /= scale
    axis_ratio = minor / max(major, 1e-9) if major > 0.0 else 0.0
    hole_fraction = (
        min(1.0, max(0.0, hole_perimeter_raw / perimeter_raw))
        if has_hole_data and perimeter_raw > 1e-9 else 0.0
    )
    hull_ratio = (
        min(1.0, max(0.0, hull_perimeter_raw / perimeter_raw))
        if hull_perimeter_raw > 1e-9 else 0.0
    )

    line_part_count = len(parts)
    component_count = 1
    if geometry is not None:
        try:
            component_count = max(1, len(geometry.geoms)) if hasattr(geometry, "geoms") else 1
        except Exception:
            component_count = 1
    segment_mean_fraction = mean_length * count / max(perimeter_scaled, 1e-9) if count else 0.0
    segment_max_fraction = max_length / max(perimeter_scaled, 1e-9) if count else 0.0
    segment_cv = std_length / max(mean_length, 1e-9) if count else 0.0
    holes_per_segment = hole_count / max(count, 1)
    boundary_complexity = (
        perimeter_raw / max(diagonal * scale, 1e-9)
        if has_perimeter and diagonal > 0.0 else 0.0
    )

    return [
        diagonal,
        aspect,
        math.log1p(line_part_count),
        math.log1p(component_count),
        hull_ratio,
        math.log1p(count),
        segment_mean_fraction,
        segment_max_fraction,
        segment_cv,
        major,
        minor,
        axis_ratio,
        math.log1p(hole_count),
        hole_fraction,
        holes_per_segment,
        boundary_complexity,
        float(polygonal is not None),
        float(entity_type == "CIRCLE"),
        float(entity_type == "ARC"),
        float(has_perimeter),
        float(has_hole_data),
    ]
