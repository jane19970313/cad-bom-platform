import math


EPSILON = 1e-6


def get_distance(point_a, point_b) -> float:
    return math.hypot(
        point_b.x - point_a.x,
        point_b.y - point_a.y,
    )


def get_unit_vector(point_a, point_b):
    dx = point_b.x - point_a.x
    dy = point_b.y - point_a.y

    length = math.hypot(dx, dy)

    if length <= EPSILON:
        return None

    return dx / length, dy / length


def are_parallel(vector_a, vector_b, tolerance=1e-3):
    dot = (
        vector_a[0] * vector_b[0]
        + vector_a[1] * vector_b[1]
    )

    return abs(abs(dot) - 1.0) <= tolerance


def project_point_onto_axis(point, origin, direction):
    return (
        (point.x - origin.x) * direction[0]
        + (point.y - origin.y) * direction[1]
    )


def get_perpendicular_distance(point, origin, direction):
    dx = point.x - origin.x
    dy = point.y - origin.y

    return abs(
        dx * direction[1]
        - dy * direction[0]
    )


def intervals_overlap(a, b, tolerance=EPSILON):
    return (
        a[0] <= b[1] + tolerance
        and b[0] <= a[1] + tolerance
    )