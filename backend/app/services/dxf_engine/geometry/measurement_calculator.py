
import math

from shapely.geometry import Point

from app.services.dxf_engine.geometry.dimension_calculator import (
    get_measured_diameter,
    get_measured_edge_length,
)

from app.services.dxf_engine.geometry.geometry_helpers import get_distance

from app.services.dxf_engine.geometry.dimension_index import DimensionIndex

from app.services.dxf_engine.models.geometry import (
    GeometryElement,
    DimensionElement,
)


EPSILON = 1e-6
CLOSURE_TOLERANCE = 1e-3
EDGE_TOLERANCE = 400.0

_HYPOT = math.hypot
_SQRT = math.sqrt
_PI = math.pi
_RADIANS = math.radians
_ROUND = round
_ABS = abs


# --------------------------------------------------
# Polygon area reconstruction
# --------------------------------------------------

def calculate_polygon_area_from_dimensions(
    polygon,
    measured_edge_lengths,
):
    """
    Reconstruct polygon coordinates using measured edge lengths
    while preserving original edge directions.

    Returns None if the reconstructed polygon does not close.
    """

    coordinates = polygon.exterior.coords
    vertex_count = len(coordinates) - 1

    if vertex_count < 3 or len(measured_edge_lengths) != vertex_count:
        return None

    reconstructed_x = 0.0
    reconstructed_y = 0.0

    previous_x = 0.0
    previous_y = 0.0

    area = 0.0

    for index, measured_length in enumerate(measured_edge_lengths):

        x1, y1 = coordinates[index]
        x2, y2 = coordinates[index + 1]

        dx = x2 - x1
        dy = y2 - y1

        geometric_length = _HYPOT(dx, dy)

        if geometric_length <= EPSILON:
            return None

        factor = measured_length / geometric_length

        reconstructed_x += dx * factor
        reconstructed_y += dy * factor

        area += (
            previous_x * reconstructed_y
            - reconstructed_x * previous_y
        )

        previous_x = reconstructed_x
        previous_y = reconstructed_y

    if _HYPOT(
        reconstructed_x,
        reconstructed_y,
    ) > CLOSURE_TOLERANCE:
        return None

    return _ABS(area) * 0.5


# --------------------------------------------------
# Circle measurement
# --------------------------------------------------

def calculate_circle_measurements(
    geometry,
    dimension_index,
    scale,
):
    """Calculate circle area and circumference."""

    center = geometry.center
    center_point = Point(center.x, center.y)

    radius = get_measured_diameter(
        center_point,
        float(geometry.radius_measured),
        dimension_index,
        scale,
    ) * 0.5

    area = _PI * radius * radius
    circumference = 2.0 * _PI * radius

    return _ROUND(area), _ROUND(circumference)


# --------------------------------------------------
# Arc measurement
# --------------------------------------------------

def calculate_arc_measurements(
    geometry,
    dimension_index,
    scale,
):
    """Calculate arc sector area and arc length."""

    center = geometry.center
    center_point = Point(center.x, center.y)

    start_angle = float(geometry.start_angle)
    end_angle = float(geometry.end_angle)

    sweep_radians = _RADIANS(
        (end_angle - start_angle) % 360.0
    )

    radius = get_measured_diameter(
        center_point,
        float(geometry.radius_measured),
        dimension_index,
        scale,
        start_angle_degree=start_angle,
        end_angle_degree=end_angle,
    ) * 0.5

    radius_squared = radius * radius

    return (
        _ROUND(0.5 * radius_squared * sweep_radians),
        _ROUND(radius * sweep_radians),
    )


# --------------------------------------------------
# LineString measurement
# --------------------------------------------------

def calculate_line_measurements(
    geometry,
    dimension_index,
    scale,
):
    """Calculate total measured LineString length."""

    coordinates = geometry.coords

    get_length = get_measured_edge_length
    edge_tolerance = EDGE_TOLERANCE

    total_length = 0.0

    for start, end in zip(coordinates[:-1], coordinates[1:]):

        measured_length = get_length(
            Point(start),
            Point(end),
            dimension_index,
            scale,
            edge_tolerance,
        )

        total_length += measured_length

    return None, _ROUND(total_length)


# --------------------------------------------------
# Polygon measurement
# --------------------------------------------------

def calculate_polygon_measurements(
    geometry,
    dimension_index,
    scale,
):
    """Calculate measured polygon area and perimeter."""

    coordinates = geometry.exterior.coords
    vertex_count = len(coordinates) - 1

    measured_edge_lengths = []
    total_perimeter = 0.0

    use_dimensions = len(coordinates) < 20

    get_edge_length = get_measured_edge_length
    get_point_distance = get_distance
    edge_tolerance = EDGE_TOLERANCE

    use_scale = scale > EPSILON

    for index in range(vertex_count):

        start = coordinates[index]
        end = coordinates[index + 1]

        if use_dimensions:

            measured_length = get_edge_length(
                Point(start),
                Point(end),
                dimension_index,
                scale,
                edge_tolerance,
            )

        else:

            geometric_length = get_point_distance(
                Point(start),
                Point(end),
            )

            measured_length = (
                geometric_length * scale
                if use_scale
                else geometric_length
            )

        measured_edge_lengths.append(measured_length)
        total_perimeter += measured_length

    area = calculate_polygon_area_from_dimensions(
        geometry,
        measured_edge_lengths,
    )

    if area is None or area < EPSILON:

        geometric_area = float(geometry.area)

        area = (
            geometric_area * scale * scale
            if use_scale
            else geometric_area
        )

    return _ROUND(area), _ROUND(total_perimeter)


# --------------------------------------------------
# Main geometry measurement
# --------------------------------------------------

def calculate_area_and_length(
    geometry: GeometryElement,
    dimension_index: DimensionIndex,
    scale: float = 0.0,
):
    """
    Calculate geometry area and length.

    Supported geometry:
        CIRCLE
        ARC
        POINT
        LINESTRING
        POLYGON
    """

    geometry_2d = geometry.geometry_2d

    if geometry_2d is None or geometry_2d.is_empty:
        return None, None

    entity_type = geometry.source.entity_type

    if entity_type == "CIRCLE":
        return calculate_circle_measurements(
            geometry,
            dimension_index,
            scale,
        )

    if entity_type == "ARC":
        return calculate_arc_measurements(
            geometry,
            dimension_index,
            scale,
        )

    geometry_type = geometry_2d.geom_type

    if geometry_type == "Point":
        return None, None

    if geometry_type == "LineString":
        return calculate_line_measurements(
            geometry_2d,
            dimension_index,
            scale,
        )

    if geometry_type == "Polygon":
        return calculate_polygon_measurements(
            geometry_2d,
            dimension_index,
            scale,
        )

    return None, None


# --------------------------------------------------
# Batch measurement assignment
# --------------------------------------------------

def assign_measurements(
    geometry_elements: list[GeometryElement],
    dimension_elements: list[DimensionElement],
    scale: float,
):
    """
    Calculate and assign area and length to all geometries.

    DimensionIndex is constructed only once.
    """

    dimension_index = (
        dimension_elements
        if isinstance(dimension_elements, DimensionIndex)
        else DimensionIndex(dimension_elements)
    )

    measurement_scale = 1.0 / scale if scale else 0.0

    calculate = calculate_area_and_length

    for geometry in geometry_elements:

        geometry.area, geometry.length = calculate(
            geometry,
            dimension_index,
            measurement_scale,
        )

    return geometry_elements
