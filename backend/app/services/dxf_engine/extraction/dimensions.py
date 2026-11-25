from shapely.geometry import (Point, Polygon, LineString)
from shapely.affinity import translate

from app.services.dxf_engine.models.geometry import (
    DimensionElement,
    TextElement,
    SourceReference
)

from statistics import median
import math

def extract_dimension_and_text_element(raw_entities, remove_handles) -> tuple[
	list[DimensionElement],
	list[TextElement]
]:
	dimension_elements: list[DimensionElement] = []
	text_elements: list[TextElement] = []
	text_guidelines: list[LineString] = []

	for entity in raw_entities:

		if entity.source.entity_handle in remove_handles:
			continue

		entity_type = entity.source.entity_type

		handle = entity.source.entity_handle
		source = entity.source

		if entity_type == "DIMENSION":
			start_point = entity.attributes.get("start_point")
			end_point = entity.attributes.get("end_point")
			center = entity.attributes.get("center")
			measurement_point = entity.attributes.get("measurement_point")
			length = entity.attributes.get("value")
			actual_length = entity.attributes.get("actual_value")

			dimension_type = entity.attributes.get(
				"dimension_type", "UNKNOWN"
			)

			endpoints = None
			definition_points_raw = entity.attributes.get("definition_points")
			definition_points = (
				tuple(Point(point[0], point[1]) for point in definition_points_raw)
				if definition_points_raw else None
			)

			if start_point is not None and end_point is not None:
				endpoints = (
					Point(start_point[0], start_point[1]),
					Point(end_point[0], end_point[1]),
				)

			if dimension_type in ("LINEAR", "ALIGNED") and endpoints is None:
				continue

			if dimension_type in ("RADIUS", "DIAMETRIC"):
				if center is None or measurement_point is None:
					continue

			dimension_elements.append(
				DimensionElement(
					element_id=handle,
					source_handle=handle,
					source=source,
					endpoints=endpoints,
					definition_points=definition_points,
					actual_length=float(actual_length) if actual_length is not None else None,
					length=float(length) if length is not None else None,
					dimension_type=dimension_type,
					center=(
						Point(center[0], center[1])
						if center is not None
						else None
					),
					measurement_point=(
						Point(measurement_point[0], measurement_point[1])
						if measurement_point is not None
						else None
					),
				)
			)
		elif entity_type == "TEXT":
			position = entity.attributes.get("center")
			corners = entity.attributes.get("corners")
			angle = entity.attributes.get("angle") or 0.0

			text_elements.append(
				TextElement(
					element_id=handle,
					source_handle=handle,
					source=source,
					position=(
						Point(position[0], position[1])
						if position is not None
						else None
					),
					position_moved=(
						Point(position[0], position[1])
						if position is not None
						else None
					),
					text=entity.text or "UNKNOWN",
					bound=(
						Polygon([(corner[0], corner[1]) for corner in corners])
						if corners
						else None
					),
                    bound_moved=(
						Polygon([(corner[0], corner[1]) for corner in corners])
						if corners
						else None
					),
					angle=math.radians(angle),
				)
			)

		elif entity_type == "LWPOLYLINE" and entity.source.layer == "TEXT":
			vertices = entity.attributes.get("vertices")
			if vertices and len(vertices) >= 2:
				text_guidelines.append(LineString(vertices))

	move_text_by_guidelines(text_guidelines, text_elements, 1000.0)

	return dimension_elements, text_elements
	

def extract_scale_from_dimensions(dimensions) -> float:
    scales = [
        dimension.endpoints[0].distance(dimension.endpoints[1])
        / dimension.actual_length
        for dimension in dimensions
        if (
            dimension.endpoints is not None
            and dimension.actual_length is not None
            and dimension.actual_length > 0
        )
    ]

    return median(scales) if scales else 1.0

def move_text_by_guidelines(text_guidelines, text_elements, tolerance):

    for text_guideline in text_guidelines:

        if text_guideline.is_empty:
            continue

        coords = list(text_guideline.coords)

        if len(coords) < 3:
            continue

        # -------------------------------------------------
        # 1. Find horizontal textside segment
        #    Only inspect the first and last segments.
        # -------------------------------------------------

        first_horizontal = (
            abs(coords[1][1] - coords[0][1]) < (0.1 * abs(coords[1][0] - coords[0][0]))
        )

        last_horizontal = (
            abs(coords[-1][1] - coords[-2][1]) < (0.1 * abs(coords[-1][0] - coords[-2][0]))
        )

        if first_horizontal:
            textside_segment = LineString([
                coords[0],
                coords[1],
            ])

            textside_endpoint = Point(coords[1])
            target_endpoint = Point(coords[-1])

        elif last_horizontal:
            textside_segment = LineString([
                coords[-2],
                coords[-1],
            ])

            textside_endpoint = Point(coords[-2])
            target_endpoint = Point(coords[0])

        else:
            continue

        # -------------------------------------------------
        # 2. Find nearest text to textside segment
        # -------------------------------------------------

        nearest_text = None
        nearest_distance = float("inf")

        for text in text_elements:

            if text.position_moved is None:
                continue

            distance = text.position_moved.distance(textside_segment)

            if distance < nearest_distance and distance <= tolerance:
                nearest_distance = distance
                nearest_text = text

        if nearest_text is None:
            continue

        # -------------------------------------------------
        # 3. Move text to target endpoint
        # -------------------------------------------------

        dx = target_endpoint.x - nearest_text.position_moved.x
        dy = target_endpoint.y - nearest_text.position_moved.y

        # Update center
        nearest_text.position_moved = Point(
            target_endpoint.x,
            target_endpoint.y,
        )

        # Update bounding polygon
        if nearest_text.bound_moved is not None:
            nearest_text.bound_moved = translate(
                nearest_text.bound_moved,
                xoff=dx,
                yoff=dy,
            )