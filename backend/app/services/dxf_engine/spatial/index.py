from shapely import STRtree
from shapely.geometry import LineString

from app.services.dxf_engine.topology.dimension_relationships import (
    _iter_segments,
)


class SpatialIndex:
    def __init__(self, geometry_elements, dimension_elements, text_elements):
        self.geometry_elements = list(geometry_elements)
        self.dimension_elements = list(dimension_elements)

        # =====================================================
        # 1. Geometry element index
        # =====================================================
        self.geometries = []
        self.indexed_elements = []

        for element in self.geometry_elements:
            geometry = element.geometry_2d

            if geometry is None or geometry.is_empty:
                continue

            self.geometries.append(geometry)
            self.indexed_elements.append(element)

        self.geometry_tree = (
            STRtree(self.geometries)
            if self.geometries
            else None
        )

        # =====================================================
        # 2. Geometry segment index
        # =====================================================
        self.segment_geometries = []
        self.indexed_segment_elements = []
        self.indexed_segment_metadata = []

        for element in self.indexed_elements:
            geometry = element.geometry_2d

            if geometry is None or geometry.is_empty:
                continue

            for segment_index, start, end, segment in _iter_segments(geometry):
                
                self.segment_geometries.append(segment)
                self.indexed_segment_elements.append(element)

                self.indexed_segment_metadata.append({
                    "segment_index": segment_index,
                    "start": start,
                    "end": end,
                })

        self.segment_tree = (
            STRtree(self.segment_geometries)
            if self.segment_geometries
            else None
        )

        # =====================================================
        # 3. Dimension element index
        # =====================================================
        self.dimensions = []
        self.indexed_dimension_elements = []

        for element in self.dimension_elements:
            if element.endpoints is None:
                continue

            p1, p2 = element.endpoints

            if p1 is None or p2 is None:
                continue

            dimension_line = LineString([
                (p1.x, p1.y),
                (p2.x, p2.y),
            ])

            if dimension_line.is_empty or dimension_line.length == 0:
                continue

            self.dimensions.append(dimension_line)
            self.indexed_dimension_elements.append(element)

        self.dimension_tree = (
            STRtree(self.dimensions)
            if self.dimensions
            else None
        )

        # =====================================================
        # 4. Radial dimension index
        # =====================================================
        self.radial_dimension_centers = []
        self.indexed_radial_dimensions = []

        for element in self.dimension_elements:
            if element.dimension_type not in ("RADIUS", "DIAMETRIC"):
                continue

            if element.center is None:
                continue

            self.radial_dimension_centers.append(element.center)
            self.indexed_radial_dimensions.append(element)

        self.radial_dimension_tree = (
            STRtree(self.radial_dimension_centers)
            if self.radial_dimension_centers
            else None
        )

    # =========================================================
    # Geometry query
    # =========================================================
    def query(self, geometry):
        if self.geometry_tree is None or geometry is None:
            return []

        indices = self.geometry_tree.query(geometry)

        return [
            self.indexed_elements[int(index)]
            for index in indices
        ]

    def nearby(self, geometry, distance: float, exclude_handle=None):
        if distance < 0:
            raise ValueError("distance cannot be negative")

        if geometry is None or geometry.is_empty:
            return []

        search_geometry = (
            geometry
            if distance == 0
            else geometry.buffer(distance)
        )

        candidates = self.query(search_geometry)

        results = []

        for element in candidates:
            if (
                exclude_handle is not None
                and element.source_handle == exclude_handle
            ):
                continue

            if element.geometry_2d.distance(geometry) <= distance:
                results.append(element)

        return results

    # =========================================================
    # Segment query
    # =========================================================
    def query_segments(self, geometry):
        if self.segment_tree is None or geometry is None:
            return []

        if geometry.is_empty:
            return []

        indices = self.segment_tree.query(geometry)

        return [
            (
                self.indexed_segment_elements[int(index)],
                self.indexed_segment_metadata[int(index)],
                self.segment_geometries[int(index)],
            )
            for index in indices
        ]

    def nearby_segments(
        self,
        geometry,
        distance: float,
        exclude_handle=None,
    ):
        if distance < 0:
            raise ValueError("distance cannot be negative")

        if geometry is None or geometry.is_empty:
            return []

        search_geometry = (
            geometry
            if distance == 0
            else geometry.buffer(distance)
        )

        candidates = self.query_segments(search_geometry)

        results = []

        for element, metadata, segment in candidates:

            if (
                exclude_handle is not None
                and element.source_handle == exclude_handle
            ):
                continue

            if segment.distance(geometry) <= distance:
                results.append(
                    (element, metadata, segment)
                )

        return results

    # =========================================================
    # Dimension query
    # =========================================================
    def query_dimen(self, geometry):
        if self.dimension_tree is None or geometry is None:
            return []

        indices = self.dimension_tree.query(geometry)

        return [
            self.indexed_dimension_elements[int(index)]
            for index in indices
        ]

    def nearby_dimen(self, geometry, distance: float, exclude_handle=None):
        if distance < 0:
            raise ValueError("distance cannot be negative")

        if geometry is None or geometry.is_empty:
            return []

        search_geometry = (
            geometry
            if distance == 0
            else geometry.buffer(distance)
        )

        candidates = self.query_dimen(search_geometry)

        results = []

        for element in candidates:

            if (
                exclude_handle is not None
                and element.source_handle == exclude_handle
            ):
                continue

            p1, p2 = element.endpoints

            if p1 is None or p2 is None:
                continue

            dimension_line = LineString([
                (p1.x, p1.y),
                (p2.x, p2.y),
            ])

            if dimension_line.distance(geometry) <= distance:
                results.append(element)

        return results

    # =========================================================
    # Radial dimension query
    # =========================================================
    def nearby_radial_dimen(
        self,
        center,
        distance: float,
        exclude_handle=None,
    ):
        if distance < 0:
            raise ValueError("distance cannot be negative")

        if center is None or self.radial_dimension_tree is None:
            return []

        search_area = (
            center
            if distance == 0
            else center.buffer(distance)
        )

        indices = self.radial_dimension_tree.query(search_area)

        results = []

        for index in indices:
            element = self.indexed_radial_dimensions[int(index)]

            if (
                exclude_handle is not None
                and element.source_handle == exclude_handle
            ):
                continue

            if element.center.distance(center) <= distance:
                results.append(element)

        return results