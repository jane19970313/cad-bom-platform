
import math

from shapely.geometry import LineString, Point

from app.services.dxf_engine.topology.dimension_relationships import (
    associate_composite_dimensions_for_segment,
)


_EPSILON = 1e-9


def _xy(point):
    """Get x, y from a Shapely Point or coordinate tuple."""
    if hasattr(point, "x"):
        return point.x, point.y

    return point[0], point[1]


def _candidate_directions(
    dimensions,
    geometries=(),
    angle_tolerance_degrees=2.0,
    max_directions=12,
    min_direction_support=1,
):
    """
    Generate a limited number of representative directions.

    Directions are treated as undirected:
    0 degrees and 180 degrees are equivalent.
    """

    angle_tolerance = math.radians(angle_tolerance_degrees)

    # angle -> accumulated direction information
    direction_groups = []

    def normalize_angle(angle):
        return angle % math.pi

    def add_direction(dx, dy):
        length = math.hypot(dx, dy)

        if length <= 1e-12:
            return

        angle = normalize_angle(math.atan2(dy, dx))

        # Find an existing direction group.
        for group in direction_groups:
            difference = abs(angle - group["angle"])
            difference = min(difference, math.pi - difference)

            if difference <= angle_tolerance:
                group["count"] += 1
                group["sin_sum"] += math.sin(2 * angle)
                group["cos_sum"] += math.cos(2 * angle)
                return

        direction_groups.append({
            "angle": angle,
            "count": 1,
            "sin_sum": math.sin(2 * angle),
            "cos_sum": math.cos(2 * angle),
        })

    # 1. Dimension directions
    for dimension in dimensions:
        if dimension.endpoints is None:
            continue

        p1, p2 = dimension.endpoints

        if p1 is None or p2 is None:
            continue

        add_direction(
            p2.x - p1.x,
            p2.y - p1.y,
        )

    # 2. Indexed geometry segment directions
    for item in geometries:
        # Supports (element, metadata, segment)
        segment = item[2] if len(item) == 3 else item

        coords = segment.coords

        if len(coords) < 2:
            continue

        start = coords[0]
        end = coords[-1]

        add_direction(
            end[0] - start[0],
            end[1] - start[1],
        )

    # 3. Rank direction groups by support
    direction_groups = [
        group
        for group in direction_groups
        if group["count"] >= min_direction_support
    ]

    direction_groups.sort(
        key=lambda group: group["count"],
        reverse=True,
    )

    # 4. Limit the number of base directions
    selected_groups = direction_groups[:max_directions]

    result = []

    for group in selected_groups:
        angle = 0.5 * math.atan2(
            group["sin_sum"],
            group["cos_sum"],
        )

        angle %= math.pi

        dx = math.cos(angle)
        dy = math.sin(angle)

        result.append((dx, dy))

    # 5. Add perpendicular directions
    base_directions = list(result)

    for dx, dy in base_directions:
        result.append((-dy, dx))

    # 6. Final deduplication
    unique = []

    for dx, dy in result:
        duplicate = False

        for ux, uy in unique:
            dot = abs(dx * ux + dy * uy)
            dot = min(1.0, max(-1.0, dot))

            angle = math.acos(dot)

            if angle <= angle_tolerance:
                duplicate = True
                break

        if not duplicate:
            unique.append((dx, dy))

    return unique


def _segment_match_score(
    real_segment,
    virtual_segment,
    angle_tolerance_degrees=2.0,
    geometry_match_tolerance=1.0,
    minimum_coverage=0.95,
    length_ratio_tolerance=0.10,
):
    """
    Match a real segment against a virtual segment.

    Requires:
        - Close distance
        - Similar direction
        - Sufficient overlap
        - Similar total lengths
    """

    distance = real_segment.distance(virtual_segment)

    if distance > geometry_match_tolerance:
        return None

    real_coords = list(real_segment.coords)
    virtual_coords = list(virtual_segment.coords)

    rx = real_coords[-1][0] - real_coords[0][0]
    ry = real_coords[-1][1] - real_coords[0][1]

    vx = virtual_coords[-1][0] - virtual_coords[0][0]
    vy = virtual_coords[-1][1] - virtual_coords[0][1]

    real_length = math.hypot(rx, ry)
    virtual_length = math.hypot(vx, vy)

    if real_length <= _EPSILON or virtual_length <= _EPSILON:
        return None

    # 1. Direction alignment
    alignment = abs(
        (rx * vx + ry * vy)
        / (real_length * virtual_length)
    )

    minimum_alignment = math.cos(
        math.radians(angle_tolerance_degrees)
    )

    if alignment < minimum_alignment:
        return None

    # 2. Project real endpoints onto virtual axis
    ux = vx / virtual_length
    uy = vy / virtual_length

    vx0, vy0 = virtual_coords[0]

    projections = [
        (x - vx0) * ux + (y - vy0) * uy
        for x, y in real_coords
    ]

    real_start = min(projections)
    real_end = max(projections)

    overlap_start = max(0.0, real_start)
    overlap_end = min(virtual_length, real_end)

    overlap = max(0.0, overlap_end - overlap_start)

    coverage = overlap / virtual_length

    if coverage < minimum_coverage:
        return None

    # 3. Compare total segment lengths
    length_ratio = real_length / virtual_length

    if abs(length_ratio - 1.0) > length_ratio_tolerance:
        return None

    return {
        "coverage": coverage,
        "distance": distance,
        "real_length": real_length,
        "virtual_length": virtual_length,
        "length_ratio": length_ratio,
        "alignment": alignment,
    }


def _find_existing_geometry_association(
    start,
    end,
    spatial_index,
    graph,
    dimensions_by_id,
    geometry_match_tolerance=1.0,
    angle_tolerance_degrees=2.0,
    minimum_coverage=0.9,
):
    virtual_segment = LineString([
        _xy(start),
        _xy(end),
    ])

    # IMPORTANT:
    # Query individual indexed segments instead of
    # scanning every segment of every geometry element.
    candidates = spatial_index.nearby_segments(
        virtual_segment,
        distance=geometry_match_tolerance,
    )

    matches = []

    for element, metadata, real_segment in candidates:

        geometry_node = ("G", element.element_id)

        if geometry_node not in graph:
            continue

        segment_index = metadata["segment_index"]

        match = _segment_match_score(
            real_segment=real_segment,
            virtual_segment=virtual_segment,
            angle_tolerance_degrees=angle_tolerance_degrees,
            geometry_match_tolerance=geometry_match_tolerance,
            minimum_coverage=minimum_coverage,
        )

        if match is None:
            continue

        # Only reuse an edge belonging to this exact segment.
        for neighbor, edge_data in graph[geometry_node].items():

            if not (
                isinstance(neighbor, tuple)
                and neighbor[0] == "D"
            ):
                continue

            dimension = dimensions_by_id.get(neighbor[1])

            if dimension is None:
                continue

            for attributes in edge_data.values():

                if attributes.get("segment_index") != segment_index:
                    continue

                association = {
                    **attributes,

                    "dimension": dimension,

                    "measurement": attributes.get(
                        "measurement",
                        getattr(
                            dimension,
                            "measurement",
                            dimension.length,
                        ),
                    ),

                    "dimension_sign": attributes.get(
                        "dimension_sign",
                        1,
                    ),

                    "dimension_order": attributes.get(
                        "dimension_order",
                        0,
                    ),

                    "projected_start": attributes.get(
                        "projected_start",
                        0.0,
                    ),

                    "projected_end": attributes.get(
                        "projected_end",
                        0.0,
                    ),

                    "perpendicular_distance": attributes.get(
                        "perpendicular_distance",
                        match["distance"],
                    ),

                    "reused_geometry_id": element.element_id,

                    "reused_segment_index": segment_index,
                }

                matches.append((
                    match["distance"],
                    -match["coverage"],
                    association,
                ))

    if not matches:
        return None

    matches.sort(
        key=lambda item: (item[0], item[1])
    )

    return matches[0][2]


def _build_virtual_right_triangle(start, end, direction):
    """
    Build two perpendicular virtual legs whose hypotenuse is start-end.

    The right-angle vertex is the projection of end onto the line
    through start in the candidate direction.
    """
    ax, ay = _xy(start)
    bx, by = _xy(end)

    hx = bx - ax
    hy = by - ay

    hypotenuse_length = math.hypot(hx, hy)

    if hypotenuse_length <= _EPSILON:
        return None

    dx, dy = direction

    projection = hx * dx + hy * dy

    # Normalize the direction so the projection is positive.
    if projection < 0:
        dx, dy = -dx, -dy
        projection = -projection

    # The right-angle vertex must lie between the hypotenuse endpoints.
    if not (
        _EPSILON
        < projection
        < hypotenuse_length - _EPSILON
    ):
        return None

    vertex = Point(
        ax + projection * dx,
        ay + projection * dy,
    )

    point_a = Point(ax, ay)
    point_b = Point(bx, by)

    leg_a_length = point_a.distance(vertex)
    leg_b_length = point_b.distance(vertex)

    if (
        leg_a_length <= _EPSILON
        or leg_b_length <= _EPSILON
    ):
        return None

    return {
        "leg_a": (point_a, vertex),
        "leg_b": (point_b, vertex),
        "leg_a_length": leg_a_length,
        "leg_b_length": leg_b_length,
        "hypotenuse_length": hypotenuse_length,
    }


def _query_nearby_dimensions(
    start,
    end,
    spatial_index,
    dimensions_by_id,
    search_distance,
    cache=None,
):
    p1 = _xy(start)
    p2 = _xy(end)

    line = LineString([p1, p2])

    # Cache key is direction-independent.
    key = (
        tuple(round(v, 8) for v in p1),
        tuple(round(v, 8) for v in p2),
        round(search_distance, 8),
    )

    if key[0] > key[1]:
        key = (key[1], key[0], key[2])

    if cache is not None and key in cache:
        return cache[key]

    candidates = spatial_index.nearby_dimen(
        line,
        distance=search_distance,
        exclude_handle=None,
    )

    results = []
    seen_ids = set()

    for candidate in candidates:

        dimension_id = candidate.element_id

        if dimension_id not in dimensions_by_id:
            continue

        if dimension_id in seen_ids:
            continue

        seen_ids.add(dimension_id)

        results.append(
            dimensions_by_id[dimension_id]
        )

    if cache is not None:
        cache[key] = results

    return results


def _match_virtual_leg(
    element,
    segment_index,
    leg_index,
    start,
    end,
    spatial_index,
    dimensions_by_id,
    graph,
    search_distance,
    geometry_match_tolerance,
    composite_options,
    dimension_query_cache=None,
):
    target_length = start.distance(end)

    # 1. Try reusing a dimension already associated with real geometry.
    existing_association = _find_existing_geometry_association(
        start=start,
        end=end,
        spatial_index=spatial_index,
        graph=graph,
        dimensions_by_id=dimensions_by_id,
        geometry_match_tolerance=geometry_match_tolerance,
    )

    if existing_association is not None:
        return {
            "leg_index": leg_index,
            "target_length": target_length,
            "associations": [existing_association],
            "source": "existing_geometry",
        }

    # 2. No reusable edge: use the existing composite matcher.
    nearby_dimensions = _query_nearby_dimensions(
        start=start,
        end=end,
        spatial_index=spatial_index,
        dimensions_by_id=dimensions_by_id,
        search_distance=search_distance,
        cache=dimension_query_cache,
    )

    if not nearby_dimensions:
        return None

    virtual_element = type(
        "VirtualGeometry",
        (),
        {
            "element_id": (
                f"{element.element_id}_SEG_{segment_index}"
                f"_PYTH_LEG_{leg_index}"
            )
        },
    )()

    associations = associate_composite_dimensions_for_segment(
        element=virtual_element,
        segment_index=0,
        start=start,
        end=end,
        dimensions=nearby_dimensions,
        search_distance=search_distance,
        **composite_options,
    )

    if not associations:
        return None

    return {
        "leg_index": leg_index,
        "target_length": target_length,
        "associations": associations,
        "source": "composite_matcher",
    }


def _score_leg(leg):
    associations = sorted(
        leg["associations"],
        key=lambda item: item.get("dimension_order", 0),
    )

    signed_measurement = sum(
        item.get("dimension_sign", 1) * item["measurement"]
        for item in associations
    )

    measurement_error = abs(
        signed_measurement - leg["target_length"]
    )

    connection_error = sum(
        abs(
            associations[i]["projected_start"]
            - associations[i - 1]["projected_end"]
        )
        for i in range(1, len(associations))
    )

    distance_error = sum(
        item.get("perpendicular_distance", 0.0)
        for item in associations
    )

    return (
        distance_error,
        measurement_error,
        connection_error,
        len(associations),
    )


def _score_triangle(leg_results):
    scores = [
        _score_leg(leg)
        for leg in leg_results
    ]

    return (
        sum(score[0] for score in scores),
        sum(score[1] for score in scores),
        sum(score[2] for score in scores),
        sum(score[3] for score in scores),
    )


def _uses_same_dimension(leg_results):
    first_ids = {
        item["dimension"].element_id
        for item in leg_results[0]["associations"]
    }

    second_ids = {
        item["dimension"].element_id
        for item in leg_results[1]["associations"]
    }

    return bool(first_ids & second_ids)


def associate_pythagorean_dimensions(
    element,
    segment_index,
    start,
    end,
    dimensions,
    spatial_index,
    graph,
    search_distance=500.0,
    geometry_match_tolerance=1.0,
    angle_tolerance_degrees=2.0,
    **composite_options,
):
    """
    Find the best Pythagorean relationship for one unresolved segment.

    Optimized:
        - Uses indexed geometry segments.
        - Avoids repeated geometry traversal.
        - Reuses cached dimension query results.
        - Reuses existing STRtree LineString objects.

    Returns:
        A list of dimension associations from both legs, or [].
    """

    if search_distance < 0:
        raise ValueError("search_distance cannot be negative")

    if geometry_match_tolerance < 0:
        raise ValueError(
            "geometry_match_tolerance cannot be negative"
        )

    if not 0 <= angle_tolerance_degrees < 90:
        raise ValueError(
            "angle_tolerance_degrees must be >= 0 and < 90"
        )

    start = Point(*_xy(start))
    end = Point(*_xy(end))

    hypotenuse_length = start.distance(end)

    if hypotenuse_length <= _EPSILON:
        return []

    # Build lookup once.
    dimensions_by_id = {
        dimension.element_id: dimension
        for dimension in dimensions
    }

    # Shared cache for this Pythagorean analysis.
    dimension_query_cache = {}

    # -----------------------------------------------------
    # 1. Query dimensions near hypotenuse.
    # -----------------------------------------------------
    orientation_dimensions = _query_nearby_dimensions(
        start=start,
        end=end,
        spatial_index=spatial_index,
        dimensions_by_id=dimensions_by_id,
        search_distance=search_distance,
        cache=dimension_query_cache,
    )

    # -----------------------------------------------------
    # 2. Query individual geometry segments near hypotenuse.
    # -----------------------------------------------------
    hypotenuse = LineString([
        _xy(start),
        _xy(end),
    ])

    orientation_segments = spatial_index.nearby_segments(
        hypotenuse,
        distance=search_distance,
    )

    # -----------------------------------------------------
    # 3. Generate candidate directions.
    # -----------------------------------------------------
    directions = _candidate_directions(
        dimensions=orientation_dimensions,
        geometries=orientation_segments,
        angle_tolerance_degrees=angle_tolerance_degrees,
        max_directions=2,
        min_direction_support=1,
    )

    if not directions:
        return []

    valid_triangles = []

    # -----------------------------------------------------
    # 4. Evaluate candidate right triangles.
    # -----------------------------------------------------
    for direction in directions:

        triangle = _build_virtual_right_triangle(
            start,
            end,
            direction,
        )

        if triangle is None:
            continue

        # ---------------------------------------------
        # Leg A
        # ---------------------------------------------
        leg_a = _match_virtual_leg(
            element=element,
            segment_index=segment_index,
            leg_index=1,
            start=triangle["leg_a"][0],
            end=triangle["leg_a"][1],
            spatial_index=spatial_index,
            dimensions_by_id=dimensions_by_id,
            graph=graph,
            search_distance=search_distance,
            geometry_match_tolerance=geometry_match_tolerance,
            composite_options=composite_options,
            dimension_query_cache=dimension_query_cache,
        )

        if leg_a is None:
            continue

        # ---------------------------------------------
        # Leg B
        # ---------------------------------------------
        leg_b = _match_virtual_leg(
            element=element,
            segment_index=segment_index,
            leg_index=2,
            start=triangle["leg_b"][0],
            end=triangle["leg_b"][1],
            spatial_index=spatial_index,
            dimensions_by_id=dimensions_by_id,
            graph=graph,
            search_distance=search_distance,
            geometry_match_tolerance=geometry_match_tolerance,
            composite_options=composite_options,
            dimension_query_cache=dimension_query_cache,
        )

        if leg_b is None:
            continue

        leg_results = [leg_a, leg_b]

        # One dimension cannot represent both perpendicular legs.
        if _uses_same_dimension(leg_results):
            continue

        valid_triangles.append(leg_results)

    if not valid_triangles:
        return []

    # -----------------------------------------------------
    # 5. Select best triangle.
    # -----------------------------------------------------
    best_triangle = min(
        valid_triangles,
        key=_score_triangle,
    )

    # -----------------------------------------------------
    # 6. Flatten associations.
    # -----------------------------------------------------
    associations = []

    for leg in best_triangle:

        for association in leg["associations"]:

            associations.append({
                **association,

                "relationship": "pythagorean",
                "method": "virtual_right_triangle",

                "geometry_role": "hypotenuse",
                "dimension_role": "leg",

                "dimension_sign": association.get(
                    "dimension_sign",
                    1,
                ),

                "leg_index": leg["leg_index"],

                "leg_target_length": leg["target_length"],
            })

    return associations