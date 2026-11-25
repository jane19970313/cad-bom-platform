
import math

from shapely.geometry import Point

from app.services.dxf_engine.geometry.geometry_helpers import get_distance
from app.services.dxf_engine.geometry.edge_calculator import (
    calculate_edge_length_from_dimensions,
)

EPSILON = 1e-6


# --------------------------------------------------
# Internal helpers
# --------------------------------------------------

def _is_valid_length(length):
    return length is not None and length > EPSILON


def _get_dimension_length(
    start,
    end,
    dimension_index,
    tolerance=1e-3,
):
    """Get a valid measured length from dimensions."""

    length = calculate_edge_length_from_dimensions(
        start,
        end,
        dimension_index,
        tolerance,
    )

    return length if _is_valid_length(length) else None


# --------------------------------------------------
# Pythagorean measurement
# --------------------------------------------------

def calculate_length_using_pythagoras(
    start,
    end,
    dimension_index,
    tolerance=1e-3,
):
    """Calculate diagonal length using measured horizontal and vertical dimensions."""

    dx = abs(end.x - start.x)
    dy = abs(end.y - start.y)

    if dx <= EPSILON or dy <= EPSILON:
        return None

    min_x = min(start.x, end.x)
    min_y = min(start.y, end.y)

    horizontal_start = Point(min_x, start.y)
    horizontal_end = Point(max(start.x, end.x), start.y)

    vertical_start = Point(end.x, min_y)
    vertical_end = Point(end.x, max(start.y, end.y))

    horizontal_length = _get_dimension_length(
        horizontal_start,
        horizontal_end,
        dimension_index,
        tolerance,
    )

    if horizontal_length is None:
        return None

    vertical_length = _get_dimension_length(
        vertical_start,
        vertical_end,
        dimension_index,
        tolerance,
    )

    if vertical_length is None:
        return None

    return math.hypot(horizontal_length, vertical_length)


# --------------------------------------------------
# Public measurement functions
# --------------------------------------------------

def get_measured_edge_length(
    start,
    end,
    dimension_index,
    scale,
    tolerance=1e-3,
):
    """
    Get edge length using:
    1. Direct dimension measurement.
    2. Pythagorean calculation for diagonals.
    3. Geometric length multiplied by scale.
    4. Geometric fallback.
    """

    geometric_length = get_distance(start, end)

    tolerance = min(tolerance, geometric_length * 0.2)

    measured_length = _get_dimension_length(
        start,
        end,
        dimension_index,
        tolerance,
    )

    if measured_length is not None:
        return measured_length

    dx = abs(end.x - start.x)
    dy = abs(end.y - start.y)

    if dx > EPSILON and dy > EPSILON:
        measured_length = calculate_length_using_pythagoras(
            start,
            end,
            dimension_index,
            tolerance,
        )

        if measured_length is not None:
            return measured_length

    if scale > EPSILON:
        return geometric_length * scale

    return geometric_length


# --------------------------------------------------
# Diameter measurement
# --------------------------------------------------

def get_measured_diameter(
    center,
    geometric_radius,
    dimension_index,
    scale,
    start_angle_degree=0.0,
    end_angle_degree=0.0,
):
    """
    Calculate measured diameter using available dimensions.

    Circles:
        Try horizontal and vertical diameters, followed by radii.

    Arcs:
        Try start and end radii.

    Fallback:
        Use geometric diameter multiplied by scale.
    """

    cx = center.x
    cy = center.y

    radius = geometric_radius

    def measure_radius(dx, dy):
        """Measure a radial edge from the center."""

        endpoint = Point(
            cx + radius * dx,
            cy + radius * dy,
        )

        return _get_dimension_length(
            center,
            endpoint,
            dimension_index,
        )

    def measure_diameter(start, end):
        """Measure a complete diameter."""

        return _get_dimension_length(
            start,
            end,
            dimension_index,
        )

    # --------------------------------------------------
    # Circle
    # --------------------------------------------------

    if start_angle_degree == end_angle_degree:

        # Horizontal diameter
        diameter = measure_diameter(
            Point(cx - radius, cy),
            Point(cx + radius, cy),
        )

        if diameter is not None:
            return diameter

        # Vertical diameter
        diameter = measure_diameter(
            Point(cx, cy - radius),
            Point(cx, cy + radius),
        )

        if diameter is not None:
            return diameter

        # Try individual radii
        for dx, dy in (
            (-1, 0),  # Left
            (1, 0),   # Right
            (0, -1),  # Top
            (0, 1),   # Bottom
        ):
            measured_radius = measure_radius(dx, dy)

            if measured_radius is not None:
                return measured_radius * 2

    # --------------------------------------------------
    # Arc
    # --------------------------------------------------

    else:

        for angle_degree in (
            start_angle_degree,
            end_angle_degree,
        ):
            angle = math.radians(angle_degree)

            measured_radius = measure_radius(
                math.cos(angle),
                math.sin(angle),
            )

            if measured_radius is not None:
                return measured_radius * 2

    # --------------------------------------------------
    # Geometric fallback
    # --------------------------------------------------

    geometric_diameter = radius * 2

    if scale > EPSILON:
        return geometric_diameter * scale

    return geometric_diameter
