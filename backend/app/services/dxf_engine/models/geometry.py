from dataclasses import dataclass, field
from typing import Any

from .source import SourceReference

from shapely.geometry import (Point, Polygon)
@dataclass
class GeometryElement:
    element_id: str
    source_handle: str
    source: SourceReference

    geometry_2d: Any | None = None

    coordinates_3d: list[
        tuple[float, float, float]
    ] = field(default_factory=list)

    center: Point | None = None
    radius: float | None = None
    radius_measured: float | None = None
    start_angle: float | None = None
    end_angle: float | None = None

    geometry_type: str = "UNKNOWN"
    caption: str = "UNKNOWN"
    text: str = ""
    text_handle: str = ""
    is_closed: bool = False
    is_valid: bool = True

    length: float | None = None
    area: float | None = None

    properties: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

@dataclass
class DimensionElement:
    element_id: str
    source_handle: str
    source: SourceReference

    # Dimension-line endpoints (projected to the annotation line).
    endpoints: tuple[Point, Point] | None = None
    # Original geometry definition/extension-origin points from DXF.
    # These are the preferred points for Dimension-to-Geometry association.
    definition_points: tuple[Point, ...] | None = None
    length: float | None = None
    actual_length: float | None = None

    dimension_type: str = "UNKNOWN"

    center: Point | None = None
    measurement_point: Point | None = None

@dataclass
class TextElement:
    element_id: str
    source_handle: str
    source: SourceReference
    
    position: Point | None = None
    position_moved: Point | None = None
    text: str = "UNKNOWN"
    bound: Polygon | None = None
    bound_moved: Polygon | None = None
    angle: float = 0.0 #radian