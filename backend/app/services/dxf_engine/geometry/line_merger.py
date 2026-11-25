from collections import defaultdict
from copy import copy
import math

from scipy.spatial import cKDTree
from shapely.geometry import MultiLineString, LineString
from shapely.ops import linemerge


def _are_segments_parallel(line, tolerance=0.001):
    coords = line.coords

    if len(coords) <= 2:
        return True

    x0, y0 = coords[0][:2]
    x1, y1 = coords[1][:2]

    dx0 = x1 - x0
    dy0 = y1 - y0

    length0 = math.hypot(dx0, dy0)

    if length0 == 0:
        return False

    for i in range(1, len(coords) - 1):
        dx = coords[i + 1][0] - coords[i][0]
        dy = coords[i + 1][1] - coords[i][1]

        length = math.hypot(dx, dy)

        if length == 0:
            continue

        if abs(dx0 * dy - dy0 * dx) > tolerance * length0 * length:
            return False

    return True


def _simplify_parallel_line(line, tolerance=0.001):
    if len(line.coords) <= 2:
        return line

    if _are_segments_parallel(line, tolerance):
        return LineString([line.coords[0], line.coords[-1]])

    return line


def _cluster_endpoints(lines, tolerance):
    endpoints = []

    for line in lines:
        coords = line.coords
        endpoints.append(coords[0][:2])
        endpoints.append(coords[-1][:2])

    if not endpoints:
        return []

    tree = cKDTree(endpoints)

    parent = list(range(len(endpoints)))
    rank = [0] * len(endpoints)

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]

        return x

    def union(a, b):
        ra = find(a)
        rb = find(b)

        if ra == rb:
            return

        if rank[ra] < rank[rb]:
            ra, rb = rb, ra

        parent[rb] = ra

        if rank[ra] == rank[rb]:
            rank[ra] += 1

    for a, b in tree.query_pairs(tolerance):
        union(a, b)

    representatives = {}

    for i, point in enumerate(endpoints):
        root = find(i)

        if root not in representatives:
            representatives[root] = point

    result = []

    for i, line in enumerate(lines):
        coords = list(line.coords)

        start = representatives[find(2 * i)]
        end = representatives[find(2 * i + 1)]

        coords[0] = (*start, *coords[0][2:])
        coords[-1] = (*end, *coords[-1][2:])

        result.append(LineString(coords))

    return result


def _update_3d_coordinates(element, merged_line):
    coords_2d = list(merged_line.coords)
    original_3d = element.coordinates_3d

    if not original_3d:
        element.coordinates_3d = [
            (x, y, 0.0) for x, y in coords_2d
        ]
        return

    original_2d = [
        (point[0], point[1])
        for point in original_3d
    ]

    tree = cKDTree(original_2d)

    _, indices = tree.query(coords_2d, k=1)

    element.coordinates_3d = [
        (x, y, original_3d[int(index)][2])
        for (x, y), index in zip(coords_2d, indices)
    ]


def _remove_duplicate_lines(elements, tolerance):
    if len(elements) <= 1:
        return elements

    unique = []
    bounds = []

    for element in elements:
        line = element.geometry_2d
        current_bounds = line.bounds

        duplicate = None

        for i, existing in enumerate(unique):
            eb = bounds[i]

            if (
                current_bounds[2] < eb[0] - tolerance
                or eb[2] < current_bounds[0] - tolerance
                or current_bounds[3] < eb[1] - tolerance
                or eb[3] < current_bounds[1] - tolerance
            ):
                continue

            if line.hausdorff_distance(existing.geometry_2d) <= tolerance:
                duplicate = existing
                break

        if duplicate is not None:
            duplicate.warnings.append(
                duplicate.source.entity_handle
                + ";"
                + element.source.entity_handle
            )
        else:
            unique.append(element)
            bounds.append(current_bounds)

    return unique


def merge_connected_lines(geometry_elements, tolerance=0.001):

    groups = defaultdict(list)
    result = []

    # GROUP BY LAYER
    for element in geometry_elements:
        geometry = element.geometry_2d

        if geometry is None or geometry.geom_type != "LineString":
            result.append(element)
            continue

        groups[element.source.layer].append(element)

    # PROCESS EACH LAYER
    for elements in groups.values():

        if len(elements) == 1:
            result.extend(elements)
            continue

        # REMOVE DUPLICATES
        unique_elements = _remove_duplicate_lines(
            elements,
            tolerance
        )

        if len(unique_elements) == 1:
            result.extend(unique_elements)
            continue

        # CLUSTER ENDPOINTS
        original_lines = [
            element.geometry_2d
            for element in unique_elements
        ]

        snapped_lines = _cluster_endpoints(
            original_lines,
            tolerance
        )

        # MERGE CONNECTED LINES
        merged = linemerge(
            MultiLineString(snapped_lines)
        )

        if merged.geom_type == "LineString":
            merged_lines = [merged]

        elif merged.geom_type == "MultiLineString":
            merged_lines = list(merged.geoms)

        else:
            result.extend(unique_elements)
            continue

        # CREATE RESULT ELEMENTS
        for merged_line in merged_lines:

            contributing = [
                element
                for element, snapped_line in zip(
                    unique_elements,
                    snapped_lines
                )
                if merged_line.covers(snapped_line)
            ]

            if not contributing:
                continue

            merged_line = _simplify_parallel_line(
                merged_line,
                tolerance
            )

            new_element = copy(contributing[0])

            new_element.warnings.append(
                ";".join(
                    element.source.entity_handle
                    for element in contributing
                )
            )

            new_element.geometry_2d = merged_line
            new_element.is_closed = merged_line.is_closed

            _update_3d_coordinates(
                new_element,
                merged_line
            )

            result.append(new_element)

    return result