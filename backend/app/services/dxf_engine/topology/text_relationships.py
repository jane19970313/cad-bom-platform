from __future__ import annotations

import math


def _geometry_orientation(geometry):
    """
    Estimate dominant geometry orientation in radians.

    Uses the longest individual line segment.
    """
    if geometry is None or geometry.is_empty:
        return None

    from .dimension_relationships import _line_parts

    best_length = 0.0
    best_angle = None

    for line in _line_parts(geometry):

        coords = list(line.coords)

        for i in range(len(coords) - 1):

            dx = coords[i + 1][0] - coords[i][0]
            dy = coords[i + 1][1] - coords[i][1]

            length = math.hypot(dx, dy)

            if length > best_length:
                best_length = length
                best_angle = math.atan2(dy, dx)

    return best_angle


def _angle_similarity(angle1, angle2):
    """
    Compare two orientations.

    Treats 0 and pi as the same line orientation.
    """
    difference = abs(angle1 - angle2) % math.pi

    difference = min(
        difference,
        math.pi - difference,
    )

    return max(
        0.0,
        1.0 - difference / (math.pi / 2),
    )


def analyze_text_candidate(
    text,
    candidate,
    search_distance: float,
):
    """
    Calculate text-to-geometry association evidence.
    """

    geometry = candidate.geometry_2d

    if geometry is None or geometry.is_empty:
        return None

    query_geometry = (
        text.bound
        if text.bound is not None
        else text.position
    )

    if query_geometry is None or query_geometry.is_empty:
        return None

    if query_geometry.distance(geometry) > search_distance:
        return None

    intersects = query_geometry.intersects(geometry)

    contained = (
        text.position is not None
        and geometry.covers(text.position)
    )

    distance = query_geometry.distance(geometry)

    proximity_score = max(
        0.0,
        1.0 - distance / max(search_distance, 1e-9),
    )

    intersection_score = 1.0 if intersects else 0.0
    containment_score = 1.0 if contained else 0.0

    geometry_angle = _geometry_orientation(geometry)

    if geometry_angle is None:
        orientation_score = 0.5
    else:
        orientation_score = _angle_similarity(
            text.angle,
            geometry_angle,
        )

    confidence = (
        0.00 * intersection_score
        + 0.40 * proximity_score
        + 0.20 * containment_score
        + 0.40 * orientation_score
    )

    return {
        "relationship": "associated_text",
        "association_method": "text_spatial_orientation",
        "confidence": round(confidence, 4),
        "distance": round(distance, 6),
        "bounding_box_intersects": intersects,
        "position_contained": contained,
        "orientation_similarity": round(
            orientation_score, 4
        ),
        "text_content": text.text,
        "text_angle": text.angle,
    }


def associate_text(
    text,
    spatial_index,
    search_distance: float,
    minimum_confidence: float = 0.40,
):
    """
    Find geometries associated with a text element.
    """

    query_geometry = (
        text.bound
        if text.bound is not None
        else text.position
    )

    if query_geometry is None or query_geometry.is_empty:
        return []

    candidates = spatial_index.nearby(
        query_geometry,
        distance=search_distance,
        exclude_handle=text.source_handle,
    )

    results = []

    for candidate in candidates:

        evidence = analyze_text_candidate(
            text=text,
            candidate=candidate,
            search_distance=search_distance,
        )

        if evidence is None:
            continue

        if evidence["confidence"] < minimum_confidence:
            continue

        results.append({
            "geometry": candidate,
            "evidence": evidence,
        })

    return results


def _is_leader_element(element):
    """
    Recognize explicitly identified DXF leader entities.
    """
    entity_type = getattr(
        element.source,
        "entity_type",
        "",
    )

    return entity_type.upper() in {
        "LEADER",
        "MULTILEADER",
    }


def _leader_endpoints(geometry):
    """
    Return the first and last points of a leader geometry.
    """
    from .dimension_relationships import _line_parts

    parts = _line_parts(geometry)

    if not parts:
        return None

    # Prefer the longest line component.
    line = max(parts, key=lambda part: part.length)

    coords = list(line.coords)

    if len(coords) < 2:
        return None

    from shapely.geometry import Point

    return Point(coords[0]), Point(coords[-1])


def associate_leader(
    text,
    leader_elements,
    spatial_index,
    text_tolerance: float,
    endpoint_tolerance: float,
):
    """
    Detect a text-to-leader-to-geometry relationship.

    Assumes the converted leader geometry is available
    as a GeometryElement.
    """

    results = []

    text_geometry = text.bound or text.position

    if text_geometry is None:
        return results

    for leader in leader_elements:

        if not _is_leader_element(leader):
            continue

        leader_geometry = leader.geometry_2d

        if leader_geometry is None or leader_geometry.is_empty:
            continue

        if text_geometry.distance(leader_geometry) > text_tolerance:
            continue

        endpoints = _leader_endpoints(leader_geometry)

        if endpoints is None:
            continue

        p1, p2 = endpoints

        # Determine which end is closer to the annotation.
        # The opposite end is treated as the arrow/target end.
        if text_geometry.distance(p1) <= text_geometry.distance(p2):
            target_endpoint = p2
        else:
            target_endpoint = p1

        candidates = spatial_index.nearby(
            target_endpoint,
            distance=endpoint_tolerance,
            exclude_handle=leader.source_handle,
        )

        targets = []

        for candidate in candidates:

            if candidate.element_id == leader.element_id:
                continue

            distance = candidate.geometry_2d.distance(
                target_endpoint
            )

            if distance > endpoint_tolerance:
                continue

            targets.append({
                "geometry": candidate,
                "distance": distance,
            })

        for target in targets:

            results.append({
                "leader": leader,
                "target": target["geometry"],
                "text_distance": text_geometry.distance(
                    leader_geometry
                ),
                "target_distance": target["distance"],
            })

    return results