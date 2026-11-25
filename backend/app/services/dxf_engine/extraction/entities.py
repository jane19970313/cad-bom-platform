
import math
from collections import Counter
from typing import Any

from ezdxf import bbox
from ezdxf.addons import text2path
from ezdxf.math import Vec3

from app.services.dxf_engine.models import (
    RawEntity,
    SourceReference,
)


ANNOTATION_TYPES = {
    "TEXT",
    "MTEXT",
    "ATTRIB",
    "ATTDEF",
    "DIMENSION",
    "LEADER",
    "MLEADER",
}


DIMENSION_NAMES = {
    0: "LINEAR",
    1: "ALIGNED",
    2: "ANGULAR",
    3: "DIAMETRIC",
    4: "RADIUS",
    5: "ANGULAR_3P",
    6: "ORDINATE",
}


# ---------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------

def _point3(point):
    """Convert an ezdxf point to a plain XYZ tuple."""
    return tuple(Vec3(point))


def _direction_to_wcs(ocs, direction):
    """Convert an OCS direction vector to a normalized WCS vector."""
    origin = ocs.to_wcs(Vec3(0, 0, 0))
    return (ocs.to_wcs(Vec3(direction)) - origin).normalize()


def get_dimension_line_endpoints(entity):
    """
    Calculate endpoints of LINEAR or ALIGNED dimension lines.

    Returns:
        ((x1, y1, z1), (x2, y2, z2))
    """
    if entity.dxftype() != "DIMENSION":
        raise ValueError("Entity must be DIMENSION")

    dimtype = entity.dimtype & 0x07

    if dimtype not in (0, 1):
        raise ValueError(
            "Only LINEAR and ALIGNED dimensions are supported"
        )

    p1 = entity.dxf.defpoint2
    p2 = entity.dxf.defpoint3
    location = entity.dxf.defpoint

    if dimtype == 0:
        angle = math.radians(entity.dxf.angle)
        dx = math.cos(angle)
        dy = math.sin(angle)
    else:
        dx = p2.x - p1.x
        dy = p2.y - p1.y

        length = math.hypot(dx, dy)

        if length <= 1e-12:
            raise ValueError(
                "Invalid aligned dimension definition points"
            )

        dx /= length
        dy /= length

    def project(point):
        t = (
            (point.x - location.x) * dx
            + (point.y - location.y) * dy
        )

        return (
            location.x + t * dx,
            location.y + t * dy,
            location.z,
        )

    return project(p1), project(p2)


def get_text_bounds(entity):
    """
    Get approximate oriented TEXT bounds using ezdxf bounding box.

    Returns oriented corners, center, angle, width and height.
    """
    if entity.dxftype() != "TEXT":
        raise ValueError("Entity must be TEXT")

    extents = bbox.extents([entity])

    if not extents.has_data:
        return None

    min_p = extents.extmin
    max_p = extents.extmax

    angle = float(entity.dxf.rotation)
    angle_rad = math.radians(angle)

    center = (
        (min_p.x + max_p.x) / 2,
        (min_p.y + max_p.y) / 2,
        (min_p.z + max_p.z) / 2,
    )

    aabb_width = max_p.x - min_p.x
    aabb_height = max_p.y - min_p.y

    width = (
        aabb_width * abs(math.cos(angle_rad))
        + aabb_height * abs(math.sin(angle_rad))
    )

    height = (
        aabb_height * abs(math.cos(angle_rad))
        + aabb_width * abs(math.sin(angle_rad))
    )

    local_corners = [
        (-width / 2, -height / 2),
        (width / 2, -height / 2),
        (width / 2, height / 2),
        (-width / 2, height / 2),
    ]

    corners = []

    for x, y in local_corners:
        wx = (
            center[0]
            + x * math.cos(angle_rad)
            - y * math.sin(angle_rad)
        )

        wy = (
            center[1]
            + x * math.sin(angle_rad)
            + y * math.cos(angle_rad)
        )

        corners.append((wx, wy, center[2]))

    return {
        "corners": corners,
        "center": center,
        "angle": angle,
        "width": width,
        "height": height,
        "aabb_width": aabb_width,
        "aabb_height": aabb_height,
    }


def get_text_oriented_bounds(entity, flattening_distance=0.01):
    """
    Calculate oriented TEXT bounds using its actual text path.

    Returns:
        {
            "oriented_corners": [...],
            "center": (x, y, z),
            "width": float,
            "height": float,
        }
    """
    if entity.dxftype() != "TEXT":
        raise TypeError("Expected a TEXT entity")

    path = text2path.make_path_from_entity(entity)
    vertices = list(
        path.flattening(distance=flattening_distance)
    )

    if not vertices:
        return None

    ocs = entity.ocs()

    angle = math.radians(
        entity.dxf.get("rotation", 0.0)
    )

    u = _direction_to_wcs(
        ocs,
        (math.cos(angle), math.sin(angle), 0),
    )

    v = _direction_to_wcs(
        ocs,
        (-math.sin(angle), math.cos(angle), 0),
    )

    n = _direction_to_wcs(ocs, (0, 0, 1))

    projected = [
        (
            point.dot(u),
            point.dot(v),
            point.dot(n),
        )
        for point in vertices
    ]

    min_u = min(p[0] for p in projected)
    max_u = max(p[0] for p in projected)

    min_v = min(p[1] for p in projected)
    max_v = max(p[1] for p in projected)

    plane_position = sum(
        p[2] for p in projected
    ) / len(projected)

    corners = [
        u * min_u + v * min_v + n * plane_position,
        u * max_u + v * min_v + n * plane_position,
        u * max_u + v * max_v + n * plane_position,
        u * min_u + v * max_v + n * plane_position,
    ]

    center = sum(
        corners,
        Vec3(0, 0, 0),
    ) / 4

    return {
        "oriented_corners": [
            tuple(point) for point in corners
        ],
        "center": tuple(center),
        "width": max_u - min_u,
        "height": max_v - min_v,
    }


# ---------------------------------------------------------------------
# LINE and POLYLINE geometry
# ---------------------------------------------------------------------

def get_line_vertices(entity):
    """
    Extract LINE endpoints in WCS.

    Returns:
        [(x1, y1, z1), (x2, y2, z2)]
    """
    if entity.dxftype() != "LINE":
        raise ValueError("Entity must be LINE")

    return [
        _point3(entity.dxf.start),
        _point3(entity.dxf.end),
    ]


def get_lwpolyline_vertices(entity):
    """
    Extract LWPOLYLINE vertices in WCS.

    LWPOLYLINE vertices are stored in OCS with a common elevation.
    This function transforms them into WCS.

    Returns:
        List of XYZ tuples.
    """
    if entity.dxftype() != "LWPOLYLINE":
        raise ValueError("Entity must be LWPOLYLINE")

    ocs = entity.ocs()

    return [
        tuple(ocs.to_wcs(Vec3(x, y, entity.dxf.elevation)))
        for x, y in entity.get_points("xy")
    ]


def get_polyline_vertices(entity):
    """
    Extract POLYLINE vertices in WCS.

    Handles both 2D and 3D POLYLINE entities.

    Returns:
        List of XYZ tuples.
    """
    if entity.dxftype() != "POLYLINE":
        raise ValueError("Entity must be POLYLINE")

    return [
        tuple(vertex.dxf.location)
        for vertex in entity.vertices
    ]

def extract_path_attributes(entity):
    """
    Extract path geometry in a consistent format.

    The vertices field can be passed directly to Shapely
    LineString for basic linear geometry.

    Bulges are retained separately because Shapely LineString
    does not support curved segments natively.
    """
    entity_type = entity.dxftype()

    if entity_type == "LINE":
        vertices = get_line_vertices(entity)

        return {
            "vertices": vertices,
            "closed": False,
            "bulges": [],
        }

    if entity_type == "LWPOLYLINE":
        vertices = get_lwpolyline_vertices(entity)

        return {
            "vertices": vertices,
            "closed": bool(entity.closed),
        }

    if entity_type == "POLYLINE":
        vertices = get_polyline_vertices(entity)

        return {
            "vertices": vertices,
            "closed": bool(entity.is_closed),
        }

    return {}


# ---------------------------------------------------------------------
# Entity-specific extraction
# ---------------------------------------------------------------------

def extract_dimension_attributes(entity):
    """Extract dimension-specific attributes."""
    dimtype = entity.dimtype & 0x07

    dimension_type = DIMENSION_NAMES.get(
        dimtype,
        "UNKNOWN",
    )

    attributes = {
        "dimension_type": dimension_type,
    }

    try:
        attributes["value"] = float(
            entity.get_measurement()
        )

        attributes["actual_value"] = float(
            entity.dxf.actual_measurement
        )
    except (AttributeError, TypeError, ValueError):
        attributes["value"] = None
        attributes["actual_value"] = None

    if dimtype in (0, 1):
        # Preserve the original geometry attachment points separately from
        # the projected dimension-line endpoints. The former identify which
        # CAD geometry is measured; the latter describe the annotation span.
        try:
            attributes["definition_points"] = (
                _point3(entity.dxf.defpoint2),
                _point3(entity.dxf.defpoint3),
            )
        except (AttributeError, TypeError, ValueError):
            attributes["definition_points"] = None

        try:
            start, end = get_dimension_line_endpoints(entity)
            attributes["start_point"] = start
            attributes["end_point"] = end
        except (AttributeError, ValueError):
            attributes["start_point"] = None
            attributes["end_point"] = None

    elif dimtype in (3, 4):
        center = entity.dxf.get("defpoint")
        measurement_point = entity.dxf.get("defpoint4")

        attributes["center"] = (
            _point3(center) if center is not None else None
        )

        attributes["measurement_point"] = (
            _point3(measurement_point)
            if measurement_point is not None
            else None
        )

    return attributes


def extract_insert_attributes(entity):
    """Extract block INSERT attributes."""
    return {
        "block_name": entity.dxf.name,
        "insert": _point3(entity.dxf.insert),
        "rotation": entity.dxf.get("rotation", 0.0),
        "xscale": entity.dxf.get("xscale", 1.0),
        "yscale": entity.dxf.get("yscale", 1.0),
        "zscale": entity.dxf.get("zscale", 1.0),
    }


def extract_circle_attributes(entity):
    """Extract CIRCLE attributes."""
    return {
        "center": _point3(entity.dxf.center),
        "radius": float(entity.dxf.radius),
    }


def extract_arc_attributes(entity):
    """Extract ARC attributes."""
    return {
        "center": _point3(entity.dxf.center),
        "radius": float(entity.dxf.radius),
        "start_angle": float(entity.dxf.start_angle),
        "end_angle": float(entity.dxf.end_angle),
    }


# ---------------------------------------------------------------------
# Main extraction
# ---------------------------------------------------------------------

def extract_modelspace(document) -> list[RawEntity]:
    """
    Extract entities from DXF modelspace.

    Each entity is converted into a RawEntity containing:
        - SourceReference
        - Common DXF attributes
        - Entity-specific geometry
        - Optional text
        - Extraction warnings
    """
    results = []
    dimension_counts = Counter()

    for entity in document.modelspace():
        entity_type = entity.dxftype()

        source = SourceReference(
            entity_handle=entity.dxf.handle,
            entity_type=entity_type,
            layer=entity.dxf.get("layer", "0"),
            layout="Model",
        )

        attributes: dict[str, Any] = {
            "color": entity.dxf.get("color"),
            "linetype": entity.dxf.get("linetype"),
            "lineweight": entity.dxf.get("lineweight"),
        }

        text = None
        warnings = []

        try:
            if entity_type == "TEXT":
                text = entity.dxf.text

                bounds = get_text_oriented_bounds(entity)

                if bounds:
                    attributes.update({
                        "corners": bounds["oriented_corners"],
                        "center": bounds["center"],
                        "width": bounds["width"],
                        "height": bounds["height"],
                        "angle": float(
                            entity.dxf.rotation
                        ),
                    })

            elif entity_type == "MTEXT":
                text = entity.text
                # Preserve placement for semantic text-node construction.
                # This is additive metadata; analytical behavior is unchanged.
                try:
                    attributes["insert"] = _point3(entity.dxf.insert)
                    attributes["angle"] = float(entity.dxf.get("rotation", 0.0))
                    attributes["char_height"] = float(entity.dxf.get("char_height", 0.0))
                    attributes["width"] = float(entity.dxf.get("width", 0.0))
                except Exception as exc:
                    warnings.append(f"Failed to extract MTEXT placement: {exc}")

            elif entity_type == "DIMENSION":
                dimension_attributes = (
                    extract_dimension_attributes(entity)
                )

                attributes.update(dimension_attributes)

                dimension_counts[
                    dimension_attributes["dimension_type"]
                ] += 1

            elif entity_type == "INSERT":
                attributes.update(
                    extract_insert_attributes(entity)
                )

            elif entity_type == "CIRCLE":
                attributes.update(
                    extract_circle_attributes(entity)
                )

            elif entity_type == "ARC":
                attributes.update(
                    extract_arc_attributes(entity)
                )

            elif entity_type in (
                "LINE",
                "LWPOLYLINE",
                "POLYLINE",
            ):
                attributes.update(
                    extract_path_attributes(entity)
                )

        except Exception as exc:
            warnings.append(
                f"Failed to extract {entity_type} geometry: {exc}"
            )

        results.append(
            RawEntity(
                source=source,
                attributes=attributes,
                text=text,
                warnings=warnings,
            )
        )

    print(
        f"[DEBUG] dimension_counts: {dimension_counts}",
        flush=True,
    )

    return results
