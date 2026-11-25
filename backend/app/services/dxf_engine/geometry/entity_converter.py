
import ezdxf
from shapely.geometry import LineString, Point, Polygon

from app.services.dxf_engine.models.geometry import (
    GeometryElement,
    SourceReference,
)


SUPPORTED_ENTITY_TYPES = frozenset({
    "LINE",
    "ARC",
    "CIRCLE",
    "LWPOLYLINE",
    "POLYLINE",
    "POINT",
    "ELLIPSE",
    "SPLINE",
})

IGNORED_LAYERS_CASEFOLD = frozenset(
    layer.casefold()
    for layer in {
        "0",
        "AXIS",
        "DIM",
        "GeSoft",
        "Num",
        "STEEL_SIGN",
        "TEXT",
        "_TSZ_PLOT_MARK",
        "桩",
        "BORDER",
    }
)


# --------------------------------------------------
# Entity properties
# --------------------------------------------------

def is_entity_closed(entity, entity_type: str) -> bool:
    """Determine whether a DXF entity represents a closed shape."""

    if entity_type in {"CIRCLE", "ELLIPSE"}:
        return True

    if entity_type == "LWPOLYLINE":
        return entity.closed

    if entity_type == "POLYLINE":
        return entity.is_closed

    return False


def should_convert_entity(entity) -> bool:
    """Apply entity type and layer filtering rules."""

    entity_type = entity.dxftype()

    if entity_type not in SUPPORTED_ENTITY_TYPES:
        return False

    layer = entity.dxf.get("layer", "0")

    if layer.casefold() in IGNORED_LAYERS_CASEFOLD:
        return False

    if (
        "开孔" in layer
        and not is_entity_closed(entity, entity_type)
    ):
        return False

    return True


# --------------------------------------------------
# Coordinate extraction
# --------------------------------------------------

def _coordinates_3d(points):
    """Convert DXF points into 3D coordinate tuples."""

    return [
        (float(p.x), float(p.y), float(p.z))
        for p in points
    ]


def _geometry_from_coordinates(coordinates_3d, is_closed):
    """Construct a Shapely geometry from extracted coordinates."""

    if not coordinates_3d:
        return None

    coordinates_2d = [
        (x, y)
        for x, y, _ in coordinates_3d
    ]

    if is_closed and len(coordinates_2d) >= 3:
        return Polygon(coordinates_2d)

    if len(coordinates_2d) >= 2:
        return LineString(coordinates_2d)

    return None


def convert_point_entity(entity):
    """Convert a DXF POINT entity."""

    point = entity.dxf.location

    coordinates_3d = [
        (
            float(point.x),
            float(point.y),
            float(point.z),
        )
    ]

    return Point(point.x, point.y), coordinates_3d


def convert_line_entity(entity):
    """Convert a DXF LINE entity."""

    start = entity.dxf.start
    end = entity.dxf.end

    coordinates_3d = [
        (
            float(start.x),
            float(start.y),
            float(start.z),
        ),
        (
            float(end.x),
            float(end.y),
            float(end.z),
        ),
    ]

    return (
        LineString([
            (start.x, start.y),
            (end.x, end.y),
        ]),
        coordinates_3d,
    )


# --------------------------------------------------
# Polyline optimization
# --------------------------------------------------

def _convert_two_point_polyline(entity, entity_type):
    """Fast conversion path for two-vertex polylines."""

    if entity_type == "LWPOLYLINE":

        if len(entity) != 2:
            return None

        elevation = float(entity.dxf.elevation)

        points = entity.get_points("xy")

        coordinates_3d = [
            (
                float(x),
                float(y),
                elevation,
            )
            for x, y in points
        ]

    elif entity_type == "POLYLINE":

        vertices = entity.vertices

        if len(vertices) != 2:
            return None

        coordinates_3d = [
            (
                float(vertex.dxf.location.x),
                float(vertex.dxf.location.y),
                float(vertex.dxf.location.z),
            )
            for vertex in vertices
        ]

    else:
        return None

    coordinates_2d = [
        (x, y)
        for x, y, _ in coordinates_3d
    ]

    return LineString(coordinates_2d), coordinates_3d


# --------------------------------------------------
# Curved and polyline conversion
# --------------------------------------------------

def convert_curved_or_polyline_entity(
    entity,
    entity_type: str,
    flattening_distance: float,
):
    """Convert curved and polyline DXF entities."""

    if entity_type in {"LWPOLYLINE", "POLYLINE"}:
        result = _convert_two_point_polyline(
            entity,
            entity_type,
        )

        if result is not None:
            return result

    path = ezdxf.path.make_path(entity)

    points = path.flattening(
        distance=flattening_distance,
        segments=8,
    )

    coordinates_3d = [
        (
            float(point.x),
            float(point.y),
            float(point.z),
        )
        for point in points
    ]

    if not coordinates_3d:
        return None, None

    is_closed = is_entity_closed(entity, entity_type)

    if entity_type == "CIRCLE":
        coordinates_2d = [
            (x, y)
            for x, y, _ in coordinates_3d
        ]

        geometry_2d = Polygon(coordinates_2d)

    else:
        geometry_2d = _geometry_from_coordinates(
            coordinates_3d,
            is_closed,
        )

    if geometry_2d is None:
        return None, None

    return geometry_2d, coordinates_3d


# --------------------------------------------------
# Geometry classification
# --------------------------------------------------

def classify_geometry(geometry_2d):
    """Determine the application geometry type."""

    geometry_type = geometry_2d.geom_type

    if geometry_type == "Polygon":
        return "CLOSED_PROFILE"

    if geometry_type == "Point":
        return "POINT"

    return "LINEAR_GEOMETRY"


# --------------------------------------------------
# Source reference
# --------------------------------------------------

def create_source_reference(entity, entity_type: str):
    """Create source metadata for a converted entity."""

    return SourceReference(
        entity_handle=entity.dxf.handle,
        entity_type=entity_type,
        layer=entity.dxf.get("layer", "0"),
        layout="Model",
    )


# --------------------------------------------------
# Main conversion
# --------------------------------------------------

def convert_entity(
    entity,
    flattening_distance: float = 0.1,
    diagnostics: list | None = None,
) -> GeometryElement | None:
    """Convert a supported DXF entity into a GeometryElement."""

    if flattening_distance <= 0:
        raise ValueError(
            "flattening_distance must be greater than zero"
        )

    entity_type = entity.dxftype()

    if entity_type not in SUPPORTED_ENTITY_TYPES:
        return None

    try:
        # Geometry extraction
        if entity_type == "POINT":
            geometry_2d, coordinates_3d = (
                convert_point_entity(entity)
            )

        elif entity_type == "LINE":
            geometry_2d, coordinates_3d = (
                convert_line_entity(entity)
            )

        else:
            geometry_2d, coordinates_3d = (
                convert_curved_or_polyline_entity(
                    entity,
                    entity_type,
                    flattening_distance,
                )
            )

        if geometry_2d is None or geometry_2d.is_empty:
            return None

        # Geometry validation
        is_valid = geometry_2d.is_valid

        warnings = (
            []
            if is_valid
            else ["Invalid or self-intersecting 2D geometry"]
        )

        handle = entity.dxf.handle

        # Geometry element
        geometry = GeometryElement(
            element_id=handle,
            source_handle=handle,
            source=create_source_reference(
                entity,
                entity_type,
            ),
            geometry_2d=geometry_2d,
            coordinates_3d=coordinates_3d,
            geometry_type=classify_geometry(geometry_2d),
            is_closed=is_entity_closed(
                entity,
                entity_type,
            ),
            is_valid=is_valid,
            warnings=warnings,
        )

        # Preserve circle and arc properties
        if entity_type in {"CIRCLE", "ARC"}:
            geometry.center = entity.dxf.center
            geometry.radius = entity.dxf.radius
            geometry.radius_measured = entity.dxf.radius

        if entity_type == "ARC":
            geometry.start_angle = float(
                entity.dxf.start_angle
            )
            geometry.end_angle = float(
                entity.dxf.end_angle
            )

        return geometry

    except Exception as exc:
        if diagnostics is not None:
            handle = entity.dxf.get("handle", "UNKNOWN")

            diagnostics.append(
                f"Could not convert entity {handle} "
                f"({entity_type}): "
                f"{type(exc).__name__}: {exc}"
            )

        return None
