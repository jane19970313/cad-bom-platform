
def _make_candidate(
    kind,
    endpoint,
    length,
    projection_error,
    line_distance,
):
    return {
        "kind": kind,
        "endpoint": endpoint,
        "length": length,
        "projection_error": projection_error,
        "line_distance": line_distance,
    }


# --------------------------------------------------
# Direct dimensions
# --------------------------------------------------

def find_direct_dimension_candidates(
    dimensions,
    edge_length,
    coverage_tolerance,
):
    candidates = []

    for dimension in dimensions:
        start_error = abs(dimension["start"])
        end_error = abs(dimension["end"] - edge_length)

        if start_error > coverage_tolerance:
            continue

        if end_error > coverage_tolerance:
            continue

        candidates.append(
            _make_candidate(
                kind="direct",
                endpoint=dimension["end"],
                length=dimension["length"],
                projection_error=(
                    max(start_error, end_error)
                    + abs(start_error - end_error)
                ),
                line_distance=dimension["line_distance"],
            )
        )

    return candidates


# --------------------------------------------------
# Consecutive dimension chains
# --------------------------------------------------

def find_consecutive_dimension_candidates(
    dimensions,
    edge_length,
    connection_tolerance,
    coverage_tolerance,
):
    candidates = []

    dimension_count = len(dimensions)

    starting_dimensions = []

    for index, dimension in enumerate(dimensions):
        start = dimension["start"]
        end = dimension["end"]

        if (
            abs(start) <= coverage_tolerance
            and 0 < end < edge_length + coverage_tolerance
        ):
            starting_dimensions.append(
                (
                    index,
                    end,
                    dimension["length"],
                    dimension["line_distance"],
                    abs(start),
                )
            )

    def search(
        current_endpoint,
        total_length,
        max_line_distance,
        start_error,
        used,
    ):
        end_error = abs(current_endpoint - edge_length)

        if (
            len(used) >= 2
            and end_error <= coverage_tolerance
        ):
            candidates.append(
                _make_candidate(
                    kind="chain",
                    endpoint=current_endpoint,
                    length=total_length,
                    projection_error=(
                        max(start_error, end_error)
                        + abs(start_error - end_error)
                    ),
                    line_distance=max_line_distance,
                )
            )
            return

        if current_endpoint >= edge_length + coverage_tolerance:
            return

        for index in range(dimension_count):
            if index in used:
                continue

            dimension = dimensions[index]

            start = dimension["start"]
            end = dimension["end"]

            if end <= current_endpoint:
                continue

            if end >= edge_length + coverage_tolerance:
                continue

            if abs(start - current_endpoint) > connection_tolerance:
                continue

            line_distance = dimension["line_distance"]

            search(
                current_endpoint=end,
                total_length=(
                    total_length + dimension["length"]
                ),
                max_line_distance=max(
                    max_line_distance,
                    line_distance,
                ),
                start_error=start_error,
                used=used | {index},
            )

    for (
        index,
        endpoint,
        length,
        line_distance,
        start_error,
    ) in starting_dimensions:

        search(
            current_endpoint=endpoint,
            total_length=length,
            max_line_distance=line_distance,
            start_error=start_error,
            used={index},
        )

    return candidates


# --------------------------------------------------
# Dimension coverage
# --------------------------------------------------

def _cover_interval(
    dimensions,
    start,
    end,
    startedge_tolerance,
    endedge_tolerance,
    connection_tolerance,
):
    """
    Cover an interval using multiple dimensions.

    Optimization priorities:
        1. Minimize total geometric mismatch.
        2. Minimize number of dimensions.
        3. Minimize maximum line distance.

    Returns:
        (
            covered,
            measured_length,
            max_line_distance,
            dim_left_pos,
            dim_right_pos,
        )
    """

    if end < start or not dimensions:
        return False, 0.0, 0.0, None, None

    valid_dimensions = []

    for index, dimension in enumerate(dimensions):
        dim_start = dimension["start"]
        dim_end = dimension["end"]

        if dim_end <= dim_start:
            continue

        if dim_end < start - startedge_tolerance:
            continue

        if dim_start > end + endedge_tolerance:
            continue

        valid_dimensions.append((
            dim_start,
            dim_end,
            dimension["length"],
            dimension["line_distance"],
            index,
        ))

    if not valid_dimensions:
        return False, 0.0, 0.0, None, None

    valid_dimensions.sort()

    count = len(valid_dimensions)

    # State:
    # (
    #     total_error,
    #     dimension_count,
    #     max_line_distance,
    #     measured_length,
    #     first_start,
    #     last_end,
    #     selected_indices,
    # )

    states = [[] for _ in range(count)]

    # Initialize possible first dimensions.

    for i, dimension in enumerate(valid_dimensions):
        (
            dim_start,
            dim_end,
            length,
            line_distance,
            original_index,
        ) = dimension

        start_error = abs(dim_start - start)

        if start_error > startedge_tolerance:
            continue

        if dim_end <= start:
            continue

        states[i].append((
            start_error,
            1,
            line_distance,
            length,
            dim_start,
            dim_end,
            (original_index,),
        ))

    # Build consecutive chains.

    for i in range(count):
        if not states[i]:
            continue

        current_end = valid_dimensions[i][1]

        for j in range(i + 1, count):
            (
                next_start,
                next_end,
                next_length,
                next_distance,
                next_index,
            ) = valid_dimensions[j]

            if next_end <= current_end:
                continue

            if next_start > end + endedge_tolerance:
                continue

            connection_error = abs(next_start - current_end)

            if connection_error > connection_tolerance:
                continue

            for state in states[i]:
                (
                    total_error,
                    dimension_count,
                    max_distance,
                    measured_length,
                    first_start,
                    last_end,
                    selected_indices,
                ) = state

                states[j].append((
                    total_error + connection_error,
                    dimension_count + 1,
                    max(max_distance, next_distance),
                    measured_length + next_length,
                    first_start,
                    next_end,
                    selected_indices + (next_index,),
                ))

    # Find globally optimal complete chain.

    best_state = None
    best_score = None

    for dimension_states in states:
        for state in dimension_states:
            (
                total_error,
                dimension_count,
                max_distance,
                measured_length,
                first_start,
                last_end,
                selected_indices,
            ) = state

            end_error = abs(last_end - end)

            if end_error > endedge_tolerance:
                continue

            score = (
                total_error + end_error,
                dimension_count,
                max_distance,
            )

            if best_score is None or score < best_score:
                best_score = score
                best_state = state

    if best_state is None:
        return False, 0.0, 0.0, None, None

    (
        total_error,
        dimension_count,
        max_line_distance,
        measured_length,
        first_start,
        last_end,
        selected_indices,
    ) = best_state

    return (
        True,
        measured_length,
        max_line_distance,
        first_start,
        last_end,
    )


# --------------------------------------------------
# Dimension subtraction
# --------------------------------------------------

def find_subtraction_dimension_candidates(
    dimensions,
    edge_length,
    connection_tolerance,
    coverage_tolerance,
):
    candidates = []

    for base_index, base in enumerate(dimensions):
        base_start = base["start"]
        base_end = base["end"]

        if (
            base_start > coverage_tolerance
            or base_end < edge_length - coverage_tolerance
        ):
            continue

        left_extension = max(0.0, -base_start)
        right_extension = max(0.0, base_end - edge_length)

        if (
            left_extension <= coverage_tolerance
            and right_extension <= coverage_tolerance
        ):
            continue

        subtraction_length = 0.0
        max_line_distance = base["line_distance"]

        final_dim_left = base_start
        final_dim_right = base_end

        other_dimensions = [
            dimension
            for index, dimension in enumerate(dimensions)
            if index != base_index
        ]

        # Subtract left extension.

        if left_extension > coverage_tolerance:
            result = _cover_interval(
                other_dimensions,
                base_start,
                0.0,
                connection_tolerance,
                coverage_tolerance,
                connection_tolerance,
            )

            covered, length, distance, dim_left, dim_right = result

            if not covered:
                continue

            subtraction_length += length
            max_line_distance = max(
                max_line_distance,
                distance,
            )

            final_dim_left = dim_right

        # Subtract right extension.

        if right_extension > coverage_tolerance:
            result = _cover_interval(
                other_dimensions,
                edge_length,
                base_end,
                coverage_tolerance,
                connection_tolerance,
                connection_tolerance,
            )

            covered, length, distance, dim_left, dim_right = result

            if not covered:
                continue

            subtraction_length += length
            max_line_distance = max(
                max_line_distance,
                distance,
            )

            final_dim_right = dim_left

        measured_length = base["length"] - subtraction_length

        if measured_length <= 0:
            continue

        start_error = abs(final_dim_left)
        end_error = abs(final_dim_right - edge_length)

        if (
            start_error > coverage_tolerance
            or end_error > coverage_tolerance
        ):
            continue

        candidates.append(
            _make_candidate(
                kind="subtraction",
                endpoint=edge_length,
                length=measured_length,
                projection_error=(
                    max(start_error, end_error)
                    + abs(start_error - end_error)
                ),
                line_distance=max_line_distance,
            )
        )

    return candidates
