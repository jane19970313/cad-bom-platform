from __future__ import annotations

import networkx as nx

from app.services.dxf_engine.topology.dimension_relationships import (
    associate_dimension,
    associate_composite_dimensions_for_segment,
    _iter_segments
)

from app.services.dxf_engine.topology.special_dimension_relationships import (
    associate_pythagorean_dimensions
)

from app.services.dxf_engine.topology.text_relationships import (
    associate_text,
    associate_leader,
)

import math

from app.services.dxf_engine.models.geometry import (
    GeometryElement,
    DimensionElement
)


def _get_source_handle(element) -> str | None:
    """Get the original DXF entity handle."""
    return (
        getattr(element, "source_handle", None)
        or getattr(
            getattr(element, "source", None),
            "entity_handle",
            None,
        )
    )


def _confidence(distance: float, tolerance: float) -> float:
    """
    Calculate a simple proximity confidence.

    This is a heuristic, not a statistical probability.
    """
    if distance <= 1e-9:
        return 1.0

    if tolerance <= 0:
        return 0.0

    return round(
        max(0.0, min(1.0, 1.0 - distance / tolerance)),
        4,
    )


def _get_line_endpoints(geometry):
    """
    Extract endpoints from open line-like geometries.

    Closed polygons are intentionally excluded.
    """
    if geometry is None or geometry.is_empty:
        return []

    if geometry.geom_type == "LineString":
        coords = list(geometry.coords)

        if len(coords) < 2:
            return []

        return [
            (coords[0][0], coords[0][1]),
            (coords[-1][0], coords[-1][1]),
        ]

    if geometry.geom_type == "MultiLineString":
        endpoints = []

        for line in geometry.geoms:
            coords = list(line.coords)

            if len(coords) >= 2:
                endpoints.extend([
                    (coords[0][0], coords[0][1]),
                    (coords[-1][0], coords[-1][1]),
                ])

        return endpoints

    return []


def _geometry_relationship(g1, g2, tolerance: float):
    """
    Determine the spatial relationship between two geometries.

    Returns:
        relationship, distance
    """
    if (
        g1 is None
        or g2 is None
        or g1.is_empty
        or g2.is_empty
    ):
        return None, None

    distance = g1.distance(g2)

    # Endpoint connectivity has higher priority than
    # general intersection.
    endpoints1 = _get_line_endpoints(g1)
    endpoints2 = _get_line_endpoints(g2)

    if endpoints1 and endpoints2:
        from shapely.geometry import Point

        endpoint_distance = min(
            Point(p1).distance(Point(p2))
            for p1 in endpoints1
            for p2 in endpoints2
        )

        if endpoint_distance <= tolerance:
            return "endpoint_connected", endpoint_distance

    if g1.touches(g2):
        return "boundary_connected", distance

    if g1.overlaps(g2):
        return "overlaps", distance

    if g1.crosses(g2):
        return "crosses", distance

    if g1.intersects(g2):
        return "intersects", distance

    if distance <= tolerance:
        return "near", distance

    return None, distance


def _get_straight_geometry_axis(element, angle_tolerance_degrees=2.0):
    """
    Return (start_point, unit_direction, length) for a straight geometry.

    Only straight LineString geometries are considered. A polyline with
    bends is not treated as one parallel entity.
    """
    geometry = element.geometry_2d

    if geometry is None or geometry.is_empty:
        return None

    if geometry.geom_type != "LineString":
        return None

    coordinates = list(geometry.coords)

    if len(coordinates) < 2:
        return None

    start = coordinates[0]
    end = coordinates[-1]

    dx = end[0] - start[0]
    dy = end[1] - start[1]

    length = math.hypot(dx, dy)

    if length <= 1e-9:
        return None

    ux = dx / length
    uy = dy / length

    # Make sure every intermediate segment follows the same axis.
    # This excludes bent polylines.
    cos_tolerance = math.cos(math.radians(angle_tolerance_degrees))

    for point_a, point_b in zip(coordinates, coordinates[1:]):
        sx = point_b[0] - point_a[0]
        sy = point_b[1] - point_a[1]

        segment_length = math.hypot(sx, sy)

        if segment_length <= 1e-9:
            continue

        segment_ux = sx / segment_length
        segment_uy = sy / segment_length

        alignment = abs(ux * segment_ux + uy * segment_uy)

        if alignment < cos_tolerance:
            return None

    return start, (ux, uy), length


def _are_parallel_equal_length(
    axis_a,
    axis_b,
    length_tolerance=1e-3,
    angle_tolerance_degrees=2.0,
):
    if axis_a is None or axis_b is None:
        return False

    _, direction_a, length_a = axis_a
    _, direction_b, length_b = axis_b

    if abs(length_a - length_b) > length_tolerance:
        return False

    dot = abs(
        direction_a[0] * direction_b[0]
        + direction_a[1] * direction_b[1]
    )

    minimum_alignment = math.cos(math.radians(angle_tolerance_degrees))

    return dot >= minimum_alignment


def _horizontal_distance_between_axes(axis_a, axis_b):
    """
    Calculate the longitudinal distance between two geometries
    using their common local axis.

    The geometry direction is treated as the local horizontal axis.
    """
    start_a, direction_a, length_a = axis_a
    start_b, direction_b, length_b = axis_b

    # Use axis_a direction as the local horizontal direction.
    ux, uy = direction_a

    # Calculate leftmost endpoints along the local axis.
    end_a = (
        start_a[0] + ux * length_a,
        start_a[1] + uy * length_a,
    )

    end_b = (
        start_b[0] + direction_b[0] * length_b,
        start_b[1] + direction_b[1] * length_b,
    )

    projection_a = [
        start_a[0] * ux + start_a[1] * uy,
        end_a[0] * ux + end_a[1] * uy,
    ]

    projection_b = [
        start_b[0] * ux + start_b[1] * uy,
        end_b[0] * ux + end_b[1] * uy,
    ]

    left_a = min(projection_a)
    left_b = min(projection_b)

    return abs(left_a - left_b)


def _perpendicular_distance_between_axes(axis_a, axis_b):
    """
    Calculate the perpendicular distance between two parallel axes.
    """
    start_a, direction_a, _ = axis_a
    start_b, _, _ = axis_b

    dx = start_b[0] - start_a[0]
    dy = start_b[1] - start_a[1]

    return abs(
        dx * direction_a[1] - dy * direction_a[0]
    )


def find_parallel_equal_length_groups(
    elements,
    length_tolerance=1e-3,
    angle_tolerance_degrees=2.0,
    position_tolerance=1.0,
):
    """
    Group straight geometry entities by:
        1. Equal length
        2. Parallel direction
        3. Local horizontal distance

    Every member must be compatible with all other
    members in the same group.

    Singleton groups are excluded.
    """

    # 1. Extract axes
    axes = {
        element.element_id: _get_straight_geometry_axis(
            element,
            angle_tolerance_degrees=angle_tolerance_degrees,
        )
        for element in elements
    }

    valid_elements = [
        element
        for element in elements
        if axes[element.element_id] is not None
    ]

    # 2. Check compatibility
    def compatible(element_a, element_b):
        return _are_parallel_equal_length(
            axes[element_a.element_id],
            axes[element_b.element_id],
            length_tolerance=length_tolerance,
            angle_tolerance_degrees=angle_tolerance_degrees,
        )

    # 3. Stage 1: Group by local horizontal distance
    groups = []

    for element in valid_elements:
        matching_group = None

        for group in groups:
            if all(
                compatible(element, member)
                and _horizontal_distance_between_axes(
                    axes[element.element_id],
                    axes[member.element_id],
                ) <= position_tolerance
                for member in group
            ):
                matching_group = group
                break

        if matching_group is not None:
            matching_group.append(element)
        else:
            # Important: Create a new group when no match exists.
            groups.append([element])

    # 4. Keep groups containing at least two elements
    result = [
        group
        for group in groups
        if len(group) >= 2
    ]

    return result


def _add_geometry_nodes(graph, elements):
    """Add geometry nodes to the graph."""

    for element in elements:
        handle = ("G", element.element_id)
        graph.add_node(
            handle,
            node_type="geometry",
            source_handle=_get_source_handle(element),
            source_type=element.source.entity_type,
            layer=element.source.layer,
            geometry_type=element.geometry_type,
            caption=element.caption,
            is_closed=element.is_closed,
            is_valid=element.is_valid,
            length=element.length,
            area=element.area,
            geometry=element.geometry_2d,
        )


def _add_dimension_nodes(graph, dimensions):
    """Add dimension nodes to the graph."""

    for dimension in dimensions:
        handle = ("D", dimension.element_id)
        graph.add_node(
            handle,
            node_type="dimension",
            source_handle=_get_source_handle(dimension),
            source_type=dimension.source.entity_type,
            length=dimension.length,
            endpoints=dimension.endpoints,
        )


def _add_text_nodes(graph, texts):
    """Add text nodes to the graph."""

    for text in texts:
        handle = ("T", text.element_id)
        graph.add_node(
            handle,
            node_type="text",
            source_handle=_get_source_handle(text),
            source_type=text.source.entity_type,
            content=text.text,
            position=text.position,
            bound=text.bound,
            angle=text.angle,
        )


def _add_geometry_relationships(
    graph,
    elements,
    spatial_index,
    tolerance: float,
):
    """
    Detect geometry-to-geometry relationships.

    STRtree retrieves candidates.
    Shapely determines actual relationships.
    """

    seen_pairs = set()

    for element in elements:

        geometry = element.geometry_2d

        if geometry is None or geometry.is_empty:
            continue

        candidates = spatial_index.nearby(
            geometry,
            distance=tolerance,
            exclude_handle=_get_source_handle(element),
        )

        for candidate in candidates:

            if candidate.element_id == element.element_id:
                continue

            # Prevent duplicate processing of A-B and B-A.
            pair = tuple(sorted([
                ("G", element.element_id),
                ("G", candidate.element_id),
            ]))

            if pair in seen_pairs:
                continue

            seen_pairs.add(pair)

            relationship, distance = _geometry_relationship(
                geometry,
                candidate.geometry_2d,
                tolerance,
            )

            if relationship is None:
                continue

            graph.add_edge(
                pair[0],
                pair[1],
                relationship=relationship,
                distance=round(distance, 6),
                confidence=_confidence(distance, tolerance),
                association_method="spatial_geometry_analysis",
            )


def _has_dimension_edge_for_segment(
    graph: nx.MultiGraph,
    element_id: str,
    segment_index: int,
) -> bool:
    geometry_node = ("G", element_id)

    if geometry_node not in graph:
        return False

    for neighbor, edge_data in graph[geometry_node].items():
        if not (
            isinstance(neighbor, tuple)
            and neighbor[0] == "D"
        ):
            continue

        for attributes in edge_data.values():
            if attributes.get("segment_index") == segment_index:
                return True

    return False


def _add_composite_dimension_relationships(
    graph: nx.MultiGraph,
    elements: list[GeometryElement],
    dimensions: list[DimensionElement],
    **association_options,
) -> None:

    for element in elements:
        geometry = element.geometry_2d

        if geometry is None or geometry.is_empty:
            continue

        for segment_index, start, end, segment in _iter_segments(geometry):

            if _has_dimension_edge_for_segment(
                graph,
                element.element_id,
                segment_index,
            ):
                continue

            associations = associate_composite_dimensions_for_segment(
                element=element,
                segment_index=segment_index,
                start=start,
                end=end,
                dimensions=dimensions,
                **association_options,
            )

            for association in associations:
                dimension = association["dimension"]

                edge_data = {
                    key: value
                    for key, value in association.items()
                    if key != "dimension"
                }

                graph.add_edge(
                    ("G", element.element_id),
                    ("D", dimension.element_id),
                    **edge_data,
                )


def _add_pythagorean_relationships(
    graph,
    elements,
    dimensions,
    spatial_index,
    search_distance=500.0,
    geometry_match_tolerance=100.0,
    angle_tolerance_degrees=5.0,
    **composite_options,
):
    for element in elements:
        geometry = element.geometry_2d

        if geometry is None or geometry.is_empty:
            continue

        for segment_index, start, end, segment in _iter_segments(geometry):

            if _has_dimension_edge_for_segment(
                graph,
                element.element_id,
                segment_index,
            ):
                continue

            associations = associate_pythagorean_dimensions(
                element=element,
                segment_index=segment_index,
                start=start,
                end=end,
                dimensions=dimensions,
                spatial_index=spatial_index,
                graph=graph,
                search_distance=search_distance,
                geometry_match_tolerance=geometry_match_tolerance,
                angle_tolerance_degrees=angle_tolerance_degrees,
                **composite_options,
            )

            if not associations:
                continue

            group_id = (
                f"{element.element_id}_SEG_"
                f"{segment_index}_PYTHAGOREAN_001"
            )

            for association in associations:
                dimension = association["dimension"]

                edge_data = {
                    key: value
                    for key, value in association.items()
                    if key != "dimension"
                }

                edge_data["segment_index"] = segment_index
                edge_data["group_id"] = group_id

                graph.add_edge(
                    ("G", element.element_id),
                    ("D", dimension.element_id),
                    **edge_data,
                )


def _add_dimension_relationships(
    graph,
    elements,
    spatial_index,
    search_distance: float,
    endpoint_tolerance: float,
    minimum_confidence: float = 0.50,
):
    for element in elements:

        associations = associate_dimension(
            element=element,
            spatial_index=spatial_index,
            search_distance=search_distance,
            endpoint_tolerance=endpoint_tolerance,
            minimum_confidence=minimum_confidence,
        )

        for association in associations:

            candidate = association["dimension"]
            evidence = association["evidence"]

            graph.add_edge(
                ("G", element.element_id),
                ("D", candidate.element_id),
                **evidence,
            )


def _propagate_dimension_edges(
    graph,
    elements,
    length_tolerance=1e-3,
    angle_tolerance_degrees=2.0,
    position_tolerance=1.0
):
    """
    If one geometry in a parallel/equal-length group is associated
    with a dimension, propagate it only to geometries that have
    no existing dimension association.
    """
    groups = find_parallel_equal_length_groups(
        elements,
        length_tolerance=length_tolerance,
        angle_tolerance_degrees=angle_tolerance_degrees,
        position_tolerance=position_tolerance,
    )

    for group in groups:
        geometry_nodes = [
            ("G", element.element_id)
            for element in group
        ]

        dimension_edges = {}

        # 이미 dimension edge가 있는 geometry는 전파 대상에서 제외
        propagation_targets = []

        for geometry_node in geometry_nodes:
            if geometry_node not in graph:
                propagation_targets.append(geometry_node)
                continue

            existing_dimensions = []

            for _, neighbor, edge_data in graph.edges(
                geometry_node,
                data=True,
            ):
                if (
                    isinstance(neighbor, tuple)
                    and neighbor[0] == "D"
                ):
                    existing_dimensions.append(neighbor)
                    dimension_edges.setdefault(
                        neighbor,
                        edge_data.copy(),
                    )

            if not existing_dimensions:
                propagation_targets.append(geometry_node)

        # 기존 dimension edge가 없는 geometry에만 전파
        for geometry_node in propagation_targets:
            for dimension_node, edge_data in dimension_edges.items():
                graph.add_edge(
                    geometry_node,
                    dimension_node,
                    **{
                        **edge_data,
                        "relationship": "parallel_equal_length_dimension",
                        "method": "dimension_propagation",
                    },
                )


def _add_text_relationships(
    graph,
    texts,
    elements,
    spatial_index,
    search_distance: float,
    minimum_confidence: float = 0.20,
):
    for text in texts:

        # Normal text association.
        associations = associate_text(
            text=text,
            spatial_index=spatial_index,
            search_distance=search_distance,
            minimum_confidence=minimum_confidence,
        )

        for association in associations:

            candidate = association["geometry"]
            evidence = association["evidence"]

            graph.add_edge(
                ("T", text.element_id),
                ("G", candidate.element_id),
                **evidence,
            )

        # Leader-based text association.
        leader_associations = associate_leader(
            text=text,
            leader_elements=elements,
            spatial_index=spatial_index,
            text_tolerance=search_distance,
            endpoint_tolerance=search_distance,
        )

        for association in leader_associations:

            leader = association["leader"]
            target = association["target"]

            graph.add_edge(
                ("T", text.element_id),
                ("G", leader.element_id),
                relationship="leader_annotation",
                association_method="leader_detection",
                distance=round(
                    association["text_distance"], 6
                ),
                confidence=1.0,
            )

            graph.add_edge(
                ("G", leader.element_id),
                ("G", target.element_id),
                relationship="leader_points_to",
                association_method="leader_endpoint",
                distance=round(
                    association["target_distance"], 6
                ),
                confidence=1.0,
            )


def build_connectivity_graph(
    elements,
    dimensions,
    texts,
    spatial_index,
    connectivity_tolerance: float = 0.0,
    dimension_search_distance: float = 10.0,
    dimension_endpoint_tolerance: float = 1.0,
    text_search_distance: float = 10.0,
    dimension_minimum_confidence: float = 0.5,
    text_minimum_confidence: float = 0.50,
):
    """
    Build a heterogeneous connectivity graph.

    Node types:
        geometry
        dimension
        text

    Relationship types:
        endpoint_connected
        boundary_connected
        overlaps
        crosses
        intersects
        near
        dimension_of
        associated_text
    """

    if connectivity_tolerance < 0:
        raise ValueError(
            "connectivity_tolerance cannot be negative"
        )

    graph = nx.MultiGraph()

    graph.graph.update({
        "graph_type": "dxf_connectivity",
        "geometry_node_count": len(elements),
        "dimension_node_count": len(dimensions),
        "text_node_count": len(texts),
        "connectivity_tolerance": connectivity_tolerance,
    })

    # 1. Add nodes.
    _add_geometry_nodes(graph, elements)
    # _add_dimension_nodes(graph, dimensions)
    # _add_text_nodes(graph, texts)

    # 2. Geometry relationships.
    _add_geometry_relationships(
        graph,
        elements,
        spatial_index,
        connectivity_tolerance,
    )

    # 3. Engineering dimension associations.
    _add_dimension_relationships(
        graph,
        elements,
        spatial_index,
        search_distance=dimension_search_distance,
        endpoint_tolerance=dimension_endpoint_tolerance,
        minimum_confidence=dimension_minimum_confidence,
    )

    _propagate_dimension_edges(
        graph,
        elements,
        length_tolerance=50,
        angle_tolerance_degrees=2.0,
        position_tolerance=150.0
    )

    # _add_composite_dimension_relationships(
    #     graph,
    #     elements,
    #     dimensions,
    #     search_distance=20000.0,
    #     angle_tolerance_degrees=2.0,
    #     endpoint_tolerance=300.0,
    #     connection_tolerance=250.0,
    #     measurement_tolerance=500.0,
    # )

    # _add_pythagorean_relationships(
    #     graph,
    #     elements,
    #     dimensions,
    #     spatial_index=spatial_index,
    #     search_distance=2000.0,
    #     geometry_match_tolerance=300.0,
    #     angle_tolerance_degrees=3.0,
    #     endpoint_tolerance=300.0,
    #     connection_tolerance=250.0,
    #     measurement_tolerance=500.0,
    # )

    # 4. Text and leader associations.
    # _add_text_relationships(
    #     graph,
    #     texts,
    #     elements,
    #     spatial_index,
    #     search_distance=text_search_distance,
    #     minimum_confidence=text_minimum_confidence,
    # )

    return graph