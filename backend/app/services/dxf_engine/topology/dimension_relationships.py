from __future__ import annotations

import math

from shapely.geometry import LineString, Point


_EPSILON = 1e-12


def _line_parts(geometry):
    """Return line-like components of a Shapely geometry."""
    if geometry is None or geometry.is_empty:
        return []

    if geometry.geom_type in ("LineString", "LinearRing"):
        return [geometry]

    if geometry.geom_type == "MultiLineString":
        return list(geometry.geoms)

    if geometry.geom_type == "Polygon":
        return [geometry.exterior, *geometry.interiors]

    if geometry.geom_type == "MultiPolygon":
        result = []
        for polygon in geometry.geoms:
            result.append(polygon.exterior)
            result.extend(polygon.interiors)
        return result

    if hasattr(geometry, "geoms"):
        result = []
        for part in geometry.geoms:
            result.extend(_line_parts(part))
        return result

    return []


def _unit_vector(p1, p2):
    """Return a normalized direction vector, or None for zero length."""
    dx = p2.x - p1.x
    dy = p2.y - p1.y
    length = math.hypot(dx, dy)

    if length <= _EPSILON:
        return None

    return dx / length, dy / length


def _iter_segments(geometry):
    """
    Yield individual straight segments.

    Each result contains:
        segment_index, start_xy, end_xy, LineString
    """
    segment_index = 0

    for line in _line_parts(geometry):
        coords = list(line.coords)

        for i in range(len(coords) - 1):
            start = (float(coords[i][0]), float(coords[i][1]))
            end = (float(coords[i + 1][0]), float(coords[i + 1][1]))

            segment = LineString([start, end])

            if segment.length <= _EPSILON:
                continue

            yield segment_index, start, end, segment
            segment_index += 1


def _project_point(point, origin, direction):
    """Signed distance along direction from origin to point."""
    dx = point.x - origin[0]
    dy = point.y - origin[1]

    return dx * direction[0] + dy * direction[1]


def _parallel_alignment(direction_a, direction_b):
    """
    Return 1 for parallel or anti-parallel vectors, 0 for perpendicular.
    """
    dot = (
        direction_a[0] * direction_b[0]
        + direction_a[1] * direction_b[1]
    )

    return min(1.0, abs(dot))


def _analyze_segment_candidate(
    segment_index,
    start,
    end,
    segment,
    candidate,
    search_distance,
    endpoint_tolerance,
    angle_tolerance_degrees,
    horizontal_tolerance=150.0,
):
    """Evaluate one geometry segment against one dimension."""
    p1, p2 = candidate.endpoints

    if p1 is None or p2 is None:
        return None

    # 1. Geometry segment direction and length.
    dx = end[0] - start[0]
    dy = end[1] - start[1]

    segment_length = math.hypot(dx, dy)

    if segment_length <= _EPSILON:
        return None

    segment_direction = (
        dx / segment_length,
        dy / segment_length,
    )

    perpendicular_direction = (
        -segment_direction[1],
        segment_direction[0],
    )

    # 2. Dimension direction check.
    dimension_direction = _unit_vector(p1, p2)

    if dimension_direction is None:
        return None

    parallel = _parallel_alignment(
        segment_direction,
        dimension_direction,
    )

    minimum_alignment = math.cos(
        math.radians(angle_tolerance_degrees)
    )

    if parallel < minimum_alignment:
        return None

    # 3. Project dimension endpoints onto local axes.
    horizontal_1 = _project_point(
        p1, start, segment_direction
    )
    horizontal_2 = _project_point(
        p2, start, segment_direction
    )

    vertical_1 = _project_point(
        p1, start, perpendicular_direction
    )
    vertical_2 = _project_point(
        p2, start, perpendicular_direction
    )

    # 4. Horizontal endpoint alignment check.
    projected_min, projected_max = sorted(
        (horizontal_1, horizontal_2)
    )

    start_error = abs(projected_min)
    end_error = abs(projected_max - segment_length)

    endpoint_error = max(start_error, end_error)

    if endpoint_error > horizontal_tolerance:
        return None

    # 5. Vertical distance check.
    vertical_distance = abs(
        (vertical_1 + vertical_2) / 2.0
    )

    vertical_deviation = abs(
        vertical_1 - vertical_2
    )

    if vertical_distance > search_distance:
        return None

    if vertical_deviation > endpoint_tolerance:
        return None

    # 6. Endpoint tolerance check.
    if endpoint_error > endpoint_tolerance:
        return None

    # 7. Confidence calculation.
    endpoint_score = (
        1.0
        if endpoint_tolerance <= 0
        else max(
            0.0,
            1.0 - endpoint_error / endpoint_tolerance,
        )
    )

    distance_score = (
        1.0
        if search_distance <= 0
        else max(
            0.0,
            1.0 - vertical_distance / search_distance,
        )
    )

    confidence = (
        0.35 * parallel
        + 0.45 * endpoint_score
        + 0.20 * distance_score
    )

    dimension_line_length = math.hypot(
        p2.x - p1.x,
        p2.y - p1.y,
    )

    return {
        "relationship": "dimension_of",
        "association_method": "segment_endpoint_projection",
        "confidence": round(confidence, 4),
        "segment_index": segment_index,
        "segment_length": round(segment_length, 6),
        "dimension_line_length": round(dimension_line_length, 6),
        "dimension_value": candidate.length,
        "parallel_alignment": round(parallel, 4),
        "projected_start": round(projected_min, 6),
        "projected_end": round(projected_max, 6),
        "projected_start_error": round(start_error, 6),
        "projected_end_error": round(end_error, 6),
        "endpoint_error": round(endpoint_error, 6),
        "horizontal_error": round(endpoint_error, 6),
        "vertical_distance": round(vertical_distance, 6),
        "vertical_deviation": round(vertical_deviation, 6),
    }


def analyze_dimension_candidate(
    element,
    candidate,
    search_distance: float,
    endpoint_tolerance: float,
    angle_tolerance_degrees: float = 15.0,
):
    """
    Find the best segment-level match between a geometry and a dimension.

    Assumption:
        candidate.endpoints are the two endpoints of the dimension line.

    Returns:
        Relationship evidence dictionary, or None.
    """
    if search_distance < 0:
        raise ValueError("search_distance cannot be negative")

    if endpoint_tolerance < 0:
        raise ValueError("endpoint_tolerance cannot be negative")

    if not 0 <= angle_tolerance_degrees < 90:
        raise ValueError(
            "angle_tolerance_degrees must be >= 0 and < 90"
        )

    geometry = element.geometry_2d

    if geometry is None or geometry.is_empty:
        return None

    best_evidence = None

    for segment_index, start, end, segment in _iter_segments(geometry):
        evidence = _analyze_segment_candidate(
            segment_index=segment_index,
            start=start,
            end=end,
            segment=segment,
            candidate=candidate,
            search_distance=search_distance,
            endpoint_tolerance=endpoint_tolerance,
            angle_tolerance_degrees=angle_tolerance_degrees,
        )

        if evidence is None:
            continue

        if (
            best_evidence is None
            or evidence["confidence"] > best_evidence["confidence"]
        ):
            best_evidence = evidence

    return best_evidence


def analyze_radial_dimension_candidate(
    element,
    candidate,
    search_distance: float,
    radius_tolerance: float,
):
    """
    Match a RADIUS or DIAMETRIC dimension to a circle or arc.
    """
    if element.center is None or element.radius is None:
        return None

    if candidate.center is None or candidate.length is None:
        return None

    if element.radius <= 0 or candidate.length <= 0:
        return None

    if candidate.dimension_type == "RADIUS":
        measured_radius = candidate.length

    elif candidate.dimension_type == "DIAMETRIC":
        measured_radius = candidate.length / 2.0

    else:
        return None

    center_distance = element.center.distance(candidate.center)

    if center_distance > search_distance:
        return None

    radius_error = abs(element.radius - measured_radius)

    if radius_error > radius_tolerance:
        return None

    center_score = (
        1.0
        if search_distance <= 0
        else max(0.0, 1.0 - center_distance / search_distance)
    )

    radius_score = (
        1.0
        if radius_tolerance <= 0
        else max(0.0, 1.0 - radius_error / radius_tolerance)
    )

    confidence = 0.4 * center_score + 0.6 * radius_score

    return {
        "relationship": "dimension_of",
        "association_method": "radial_center_and_radius",
        "confidence": round(confidence, 4),
        "dimension_type": candidate.dimension_type,
        "geometry_radius": round(element.radius, 6),
        "dimension_radius": round(measured_radius, 6),
        "center_distance": round(center_distance, 6),
        "radius_difference": round(radius_error, 6),
    }


def project_dimensions_onto_line(
    start,
    end,
    dimensions,
    search_distance=10.0,
    angle_tolerance_degrees=2.0,
    endpoint_tolerance=1.0,
):
    """
    Project linear dimensions onto a target line.

    Returns candidate dimension intervals measured along the target line.
    """
    dx = end.x - start.x
    dy = end.y - start.y
    target_length = math.hypot(dx, dy)

    if target_length <= 1e-9:
        return []

    ux = dx / target_length
    uy = dy / target_length

    min_alignment = math.cos(
        math.radians(angle_tolerance_degrees)
    )

    candidates = []

    for dimension in dimensions:
        if dimension.endpoints is None:
            continue

        p1, p2 = dimension.endpoints

        ddx = p2.x - p1.x
        ddy = p2.y - p1.y
        dimension_length = math.hypot(ddx, ddy)

        if dimension_length <= 1e-9:
            continue

        dux = ddx / dimension_length
        duy = ddy / dimension_length

        alignment = abs(ux * dux + uy * duy)

        if alignment < min_alignment:
            continue

        # Both endpoints must be sufficiently close to the target axis.
        def perpendicular_distance(point):
            px = point.x - start.x
            py = point.y - start.y
            return abs(px * uy - py * ux)

        distance = max(
            perpendicular_distance(p1),
            perpendicular_distance(p2),
        )

        if distance > search_distance:
            continue

        def project(point):
            return (
                (point.x - start.x) * ux
                + (point.y - start.y) * uy
            )

        projected_1 = project(p1)
        projected_2 = project(p2)

        interval_start = min(projected_1, projected_2)
        interval_end = max(projected_1, projected_2)

        # Reject dimensions outside the target line.
        if interval_start < -endpoint_tolerance:
            continue

        if interval_end > target_length + endpoint_tolerance:
            continue

        measurement = dimension.length

        if measurement is None or measurement <= 0:
            continue

        candidates.append({
            "dimension": dimension,
            "dimension_id": dimension.element_id,
            "projected_start": max(0.0, interval_start),
            "projected_end": min(target_length, interval_end),
            "measurement": measurement,
            "perpendicular_distance": distance,
            "traversal_direction": (
                1 if projected_2 >= projected_1 else -1
            ),
        })

    return candidates


def find_non_overlapping_dimension_chains(
    candidates,
    target_length,
    connection_tolerance=1.0,
    measurement_tolerance=1.0,
):
    """
    Find continuous, non-overlapping dimension chains covering
    the complete target line.

    Each dimension is used at most once in a chain.
    """
    ordered = sorted(
        candidates,
        key=lambda item: item["projected_start"],
    )

    results = []

    def search(
        current_position,
        chain,
        used_ids,
        measurement_sum,
    ):
        if abs(current_position - target_length) <= connection_tolerance:
            if abs(measurement_sum - target_length) <= measurement_tolerance:
                results.append(list(chain))
            return

        for candidate in ordered:
            dimension_id = candidate["dimension_id"]

            if dimension_id in used_ids:
                continue

            candidate_start = candidate["projected_start"]
            candidate_end = candidate["projected_end"]

            # Must connect to the previous interval.
            if abs(candidate_start - current_position) > connection_tolerance:
                continue

            # Reject actual overlap.
            if candidate_start < current_position - 1e-9:
                continue

            if candidate_end <= current_position:
                continue

            chain.append(candidate)
            used_ids.add(dimension_id)

            search(
                candidate_end,
                chain,
                used_ids,
                measurement_sum + candidate["measurement"],
            )

            used_ids.remove(dimension_id)
            chain.pop()

    # A valid chain must begin at the target line's start.
    for candidate in ordered:
        if candidate["projected_start"] > connection_tolerance:
            continue

        search(
            candidate["projected_end"],
            [candidate],
            {candidate["dimension_id"]},
            candidate["measurement"],
        )

    return results


def select_best_dimension_chain(chains, target_length):
    """
    Select exactly one best dimension chain.
    """
    if not chains:
        return []

    def score(chain):
        first = chain[0]
        last = chain[-1]

        measurement_error = abs(
            sum(item["measurement"] for item in chain)
            - target_length
        )
        
        coverage_error = abs(
            first["projected_start"]
        ) + abs(
            last["projected_end"] - target_length
        )

        distance_error = sum(
            item["perpendicular_distance"]
            for item in chain
        )

        connection_error = sum(
            abs(
                chain[i]["projected_start"]
                - chain[i - 1]["projected_end"]
            )
            for i in range(1, len(chain))
        )

        return (
            distance_error,
            coverage_error,
            connection_error,
            measurement_error,
            len(chain),
        )

    return min(chains, key=score)


def select_best_case_a_combination(
    combinations,
    target_length,
):
    """
    Select exactly one best Case A combination.

    Case A:
        One full dimension (+)
        minus one or more contained dimensions (-).
    """

    if not combinations:
        return []

    def score(combination):
        signed_measurement = sum(
            item["dimension_sign"] * item["measurement"]
            for item in combination
        )

        measurement_error = abs(
            signed_measurement - target_length
        )

        distance_error = sum(
            item["perpendicular_distance"]
            for item in combination
        )

        return (
            measurement_error,
            distance_error,
            len(combination),
        )

    return min(combinations, key=score)


def select_best_case_b_combination(
    combinations,
    target_length,
):
    """
    Select exactly one best signed dimension combination.
    """

    if not combinations:
        return []

    def score(combination):
        signed_measurement = sum(
            item["dimension_sign"] * item["measurement"]
            for item in combination
        )

        measurement_error = abs(
            signed_measurement - target_length
        )

        distance_error = sum(
            item["perpendicular_distance"]
            for item in combination
        )

        return (
            measurement_error,
            distance_error,
            len(combination),
        )

    return min(combinations, key=score)


def associate_composite_dimensions_for_segment(
    element,
    segment_index,
    start,
    end,
    dimensions,
    search_distance=10.0,
    angle_tolerance_degrees=2.0,
    endpoint_tolerance=1.0,
    connection_tolerance=1.0,
    measurement_tolerance=1.0,
):
    # Accept either Shapely Points or (x, y) tuples.
    start_x, start_y = (
        (start.x, start.y) if isinstance(start, Point) else start[:2]
    )
    end_x, end_y = (
        (end.x, end.y) if isinstance(end, Point) else end[:2]
    )

    segment_dx = end_x - start_x
    segment_dy = end_y - start_y
    target_length = math.hypot(segment_dx, segment_dy)

    if target_length <= 1e-9:
        return []

    start_point = Point(start_x, start_y)
    end_point = Point(end_x, end_y)

    candidates = project_dimensions_onto_line(
        start=start_point,
        end=end_point,
        dimensions=dimensions,
        search_distance=search_distance,
        angle_tolerance_degrees=angle_tolerance_degrees,
        endpoint_tolerance=endpoint_tolerance,
    )

    # if element.element_id == "4DA2" and segment_index == 1:
    #     print(f"element_id {element.element_id} - segment_index: {segment_index} start: {start_point} end: {end_point}", flush=True)
    #     for candidate in candidates:
    #         print(f"associate composite candidate: {candidate}", flush=True)

    # Case 1: Non-overlapping additive chains.
    chains = find_non_overlapping_dimension_chains(
        candidates,
        target_length,
        connection_tolerance,
        measurement_tolerance,
    )

    best_chain = None

    if chains:
        best_chain = select_best_dimension_chain(
            chains,
            target_length,
        )

    else:
        # Case A: One full dimension minus contained dimensions.
        combinations = find_case_a_combinations(
            candidates,
            target_length,
            endpoint_tolerance,
            measurement_tolerance,
        )

        if combinations:
            best_chain = select_best_case_a_combination(
                combinations,
                target_length,
            )

        else:
            # Case B: General overlapping combinations.
            combinations = find_case_b_combinations(
                candidates,
                target_length,
                endpoint_tolerance,
                measurement_tolerance,
            )

            best_chain = select_best_case_b_combination(
                combinations,
                target_length,
            )

    if not best_chain:
        return []

    chain_id = f"{element.element_id}_SEG_{segment_index}_CHAIN_001"

    associations = []

    for order, candidate in enumerate(best_chain, start=1):
        associations.append({
            "dimension": candidate["dimension"],
            "relationship": "composite_dimension_match",
            "method": "dimension_chain_projection",
            "segment_index": segment_index,
            "chain_id": chain_id,
            "dimension_order": order,
            "dimension_sign": 1,
            "traversal_direction": candidate["traversal_direction"],
            "projected_start": candidate["projected_start"],
            "projected_end": candidate["projected_end"],
            "measurement": candidate["measurement"],
        })

    return associations


def find_case_a_combinations(
    candidates,
    target_length,
    endpoint_tolerance=1.0,
    measurement_tolerance=1.0,
):
    """
    Find combinations consisting of:
        one full-length dimension
        minus one or more contained dimensions.
    """
    results = []

    for full in candidates:
        full_start = full["projected_start"]
        full_end = full["projected_end"]

        # The dimension must cover the target segment.
        if full_start > endpoint_tolerance:
            continue

        if full_end < target_length - endpoint_tolerance:
            continue

        contained = []

        for candidate in candidates:
            if candidate["dimension_id"] == full["dimension_id"]:
                continue

            # Candidate must be geometrically contained
            # within the full dimension interval.
            if (
                candidate["projected_start"] >= full_start - endpoint_tolerance
                and candidate["projected_end"] <= full_end + endpoint_tolerance
                and candidate["projected_end"] > candidate["projected_start"]
            ):
                contained.append(candidate)

        # Search for subsets of contained dimensions whose
        # measurements can be subtracted from the full measurement.
        def search(index, selected, subtraction_sum):
            signed_measurement = (
                full["measurement"] - subtraction_sum
            )

            if (
                abs(signed_measurement - target_length)
                <= measurement_tolerance
            ):
                results.append([
                    {**full, "dimension_sign": 1},
                    *[
                        {**item, "dimension_sign": -1}
                        for item in selected
                    ],
                ])

            if index >= len(contained):
                return

            for i in range(index, len(contained)):
                item = contained[i]

                selected.append(item)

                search(
                    i + 1,
                    selected,
                    subtraction_sum + item["measurement"],
                )

                selected.pop()

        search(0, [], 0.0)

    return results


def find_case_b_combinations(
    candidates,
    target_length,
    endpoint_tolerance=1.0,
    measurement_tolerance=1.0,
    max_candidates=18,
    max_search_nodes=100_000,
    max_results=1000,
):
    """
    Find overlapping dimension combinations.

    A valid combination must:
      1. Cover the target interval exactly once using signed intervals.
      2. Have a signed measurement sum matching target_length.
      3. Use at least two dimensions.

    Each dimension can have sign +1, -1, or be unused.
    """

    if target_length <= 0:
        return []

    if not candidates:
        return []

    # Prepare valid intervals.
    prepared = []
    seen_ids = set()

    for candidate in candidates:
        dimension_id = candidate["dimension_id"]

        if dimension_id in seen_ids:
            continue

        start = candidate["projected_start"]
        end = candidate["projected_end"]
        measurement = candidate["measurement"]

        if measurement is None or measurement <= 0:
            continue

        # Reject intervals extending too far outside the target.
        if start < -endpoint_tolerance:
            continue

        if end > target_length + endpoint_tolerance:
            continue

        clipped_start = max(0.0, start)
        clipped_end = min(target_length, end)

        if clipped_end <= clipped_start:
            continue

        prepared.append({
            **candidate,
            "_start": clipped_start,
            "_end": clipped_end,
        })

        seen_ids.add(dimension_id)

    if len(prepared) < 2:
        return []

    # if len(prepared) > max_candidates:
    #     raise ValueError(
    #         f"Too many candidates for Case B: {len(prepared)}. "
    #         f"Maximum allowed: {max_candidates}."
    #     )

    # Build elementary intervals using every projected endpoint.
    breakpoints = sorted({
        0.0,
        target_length,
        *[item["_start"] for item in prepared],
        *[item["_end"] for item in prepared],
    })

    cells = [
        (breakpoints[i], breakpoints[i + 1])
        for i in range(len(breakpoints) - 1)
        if breakpoints[i + 1] - breakpoints[i] > 1e-9
    ]

    # Determine which cells each dimension covers.
    active_cells = []

    for item in prepared:
        covered = []

        for cell_index, (cell_start, cell_end) in enumerate(cells):
            midpoint = (cell_start + cell_end) / 2.0

            if item["_start"] <= midpoint < item["_end"]:
                covered.append(cell_index)

        active_cells.append(covered)

    # Number of remaining dimensions capable of affecting each cell.
    remaining_counts = [
        [0] * len(cells)
        for _ in range(len(prepared) + 1)
    ]

    for i in range(len(prepared) - 1, -1, -1):
        remaining_counts[i] = remaining_counts[i + 1].copy()

        for cell_index in active_cells[i]:
            remaining_counts[i][cell_index] += 1

    results = []
    coverage = [0] * len(cells)
    selected = []

    search_nodes = 0

    search_truncated = False
    def search(index, signed_measurement):
        nonlocal search_nodes, search_truncated

        if search_nodes >= max_search_nodes:
            search_truncated = True
            return

        search_nodes += 1

        if search_nodes > max_search_nodes:
            return

        # Every cell must still be capable of reaching coverage 1.
        for cell_index in range(len(cells)):
            current = coverage[cell_index]
            remaining = remaining_counts[index][cell_index]

            if current - remaining > 1:
                return

            if current + remaining < 1:
                return

        # Measurement feasibility check.
        remaining_measurement = sum(
            abs(prepared[i]["measurement"])
            for i in range(index, len(prepared))
        )

        if (
            signed_measurement + remaining_measurement
            < target_length - measurement_tolerance
        ):
            return

        if (
            signed_measurement - remaining_measurement
            > target_length + measurement_tolerance
        ):
            return

        # All candidates have been considered.
        if index == len(prepared):
            if len(selected) < 2:
                return

            if any(value != 1 for value in coverage):
                return

            if (
                abs(signed_measurement - target_length)
                > measurement_tolerance
            ):
                return

            combination = []

            for item, sign in selected:
                combination.append({
                    key: value
                    for key, value in item.items()
                    if not key.startswith("_")
                } | {
                    "dimension_sign": sign,
                })

            combination.sort(
                key=lambda item: (
                    item["projected_start"],
                    item["projected_end"],
                    item["dimension_id"],
                )
            )

            results.append(combination)
            return

        item = prepared[index]

        # Try +1, -1, and unused.
        for sign in (1, -1, 0):

            if sign != 0:
                for cell_index in active_cells[index]:
                    coverage[cell_index] += sign

                selected.append((item, sign))

            search(
                index + 1,
                signed_measurement + sign * item["measurement"],
            )

            if sign != 0:
                selected.pop()

                for cell_index in active_cells[index]:
                    coverage[cell_index] -= sign

            if len(results) >= max_results:
                search_truncated = True
                return

            if search_nodes > max_search_nodes:
                return

    search(0, 0.0)

    if search_truncated:
        import warnings

        warnings.warn(
            f"Case B search was truncated. "
            f"Candidates: {len(prepared)}, "
            f"Search nodes: {search_nodes}, "
            f"Valid combinations found: {len(results)}. "
            f"The selected combination may not be globally optimal.",
            RuntimeWarning,
        )

    return results


def associate_dimension(
    element,
    spatial_index,
    search_distance: float,
    endpoint_tolerance: float,
    minimum_confidence: float = 0.65,
):
    if search_distance < 0:
        raise ValueError("search_distance cannot be negative")

    if endpoint_tolerance < 0:
        raise ValueError("endpoint_tolerance cannot be negative")

    geometry = element.geometry_2d

    if geometry is None or geometry.is_empty:
        return []

    results = []

    # Linear and aligned dimensions
    candidates = spatial_index.nearby_dimen(
        geometry,
        distance=search_distance,
        exclude_handle=element.source_handle,
    )

    for candidate in candidates:
        evidence = analyze_dimension_candidate(
            element=element,
            candidate=candidate,
            search_distance=search_distance,
            endpoint_tolerance=endpoint_tolerance,
        )

        if evidence is None:
            continue

        if evidence["confidence"] < minimum_confidence:
            continue

        results.append({
            "dimension": candidate,
            "evidence": evidence,
        })

    # Radius and diameter dimensions
    if (
        element.center is not None
        and element.radius is not None
    ):
        radial_candidates = spatial_index.nearby_radial_dimen(
            center=element.center,
            distance=search_distance,
            exclude_handle=element.source_handle,
        )

        for candidate in radial_candidates:
            evidence = analyze_radial_dimension_candidate(
                element=element,
                candidate=candidate,
                search_distance=search_distance,
                radius_tolerance=endpoint_tolerance,
            )

            if evidence is None:
                continue

            if evidence["confidence"] < minimum_confidence:
                continue

            results.append({
                "dimension": candidate,
                "evidence": evidence,
            })

    return sorted(
        results,
        key=lambda item: item["evidence"]["confidence"],
        reverse=True,
    )