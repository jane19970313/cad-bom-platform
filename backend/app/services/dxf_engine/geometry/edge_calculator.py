import math

from app.services.dxf_engine.geometry.geometry_helpers import (
    get_distance,
    get_unit_vector,
)

from app.services.dxf_engine.geometry.dimension_index import (
    DimensionIndex,
)

from app.services.dxf_engine.geometry.dimension_projection import (
    project_dimensions,
)

from app.services.dxf_engine.geometry.dimension_candidates import (
    find_direct_dimension_candidates,
    find_consecutive_dimension_candidates,
    find_subtraction_dimension_candidates,
)


EPSILON = 1e-6


def _get_candidate_score(
    candidate,
    projection_weight=1.0,
    line_distance_weight=1.0,
):
    """
    Lower score means a better candidate.
    """

    return (
        projection_weight * candidate["projection_error"]
        + line_distance_weight * candidate["line_distance"]
    )


def _select_best_candidate(
    candidates,
    projection_weight=1.0,
    line_distance_weight=1.0,
):
    if not candidates:
        return None

    return min(
        candidates,
        key=lambda candidate: _get_candidate_score(
            candidate,
            projection_weight,
            line_distance_weight,
        ),
    )


def calculate_edge_length_from_dimensions(
    start,
    end,
    dimension_index: DimensionIndex,
    coverage_tolerance: float = 1e-3,
    connection_tolerance: float = 1e-3,
    parallel_tolerance: float = 0.1,
    projection_weight: float = 20.0,
    line_distance_weight: float = 1.0,
) -> float | None:
    """
    Calculate edge length using available dimensions.

    Priority is determined by candidate quality:

        1. Direct dimensions.
        2. Consecutive dimension chains.
        3. Dimension subtraction.

    Candidate quality considers:

        - Projection endpoint error.
        - Perpendicular distance from target edge.

    Returns:
        Best measured length or None.
    """

    geometric_length = get_distance(start, end)

    if (
        not math.isfinite(geometric_length)
        or geometric_length <= EPSILON
    ):
        return None

    direction = get_unit_vector(start, end)

    if direction is None:
        return None

    # --------------------------------------------------
    # Project all dimensions and remove duplicates
    # --------------------------------------------------

    dimensions = project_dimensions(
        dimension_index=dimension_index,
        edge_start=start,
        edge_direction=direction,
        parallel_tolerance=parallel_tolerance,
    )

    if not dimensions:
        return None

    # --------------------------------------------------
    # Generate candidates
    # --------------------------------------------------

    candidates = []

    candidates.extend(
        find_direct_dimension_candidates(
            dimensions,
            geometric_length,
            coverage_tolerance,
        )
    )

    candidates.extend(
        find_consecutive_dimension_candidates(
            dimensions,
            geometric_length,
            connection_tolerance,
            coverage_tolerance,
        )
    )

    if not candidates:

        candidates.extend(
            find_subtraction_dimension_candidates(
                dimensions,
                geometric_length,
                connection_tolerance,
                coverage_tolerance,
            )
        )

    # --------------------------------------------------
    # Select best candidate
    # --------------------------------------------------

    best_candidate = _select_best_candidate(
        candidates,
        projection_weight=projection_weight,
        line_distance_weight=line_distance_weight,
    )

    if best_candidate is None:
        return None

    return best_candidate["length"]