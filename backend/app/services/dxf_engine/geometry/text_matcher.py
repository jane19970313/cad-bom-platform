
import math
import re

from app.services.dxf_engine.models.geometry import (
    GeometryElement,
    TextElement,
)


# ==================================================
# Configuration
# ==================================================

ACCEPTED_LAYER_CANDIDATES = {
    "MainBeam",
    "SubBeam",
    "BEAM",
    "铺板次梁",
    "Gjlx",
}

ANGLE_TOLERANCE = math.radians(5)
ZERO_TOLERANCE = 1e-9

CENTROID_DISTANCE_WEIGHT = 0.3
BOUND_DISTANCE_WEIGHT = 0.7

DIAMETER_PATTERN = re.compile(
    r"(.*?)%%C(\d+(?:\.\d+)?)",
    re.DOTALL,
)

OPENING_PATTERN = re.compile(
    r"开孔\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)"
)

TEXT_REPLACEMENTS = {
    "": "I",
    "": "I",
    "工": "I",
    "(后装)": "",
}


# ==================================================
# Direction matching
# ==================================================

def is_parallel(
    text_angle: float,
    point_1: tuple[float, float, float],
    point_2: tuple[float, float, float],
    tolerance: float = ANGLE_TOLERANCE,
) -> bool:

    dx = point_2[0] - point_1[0]
    dy = point_2[1] - point_1[1]

    if abs(dx) <= ZERO_TOLERANCE and abs(dy) <= ZERO_TOLERANCE:
        return False

    geometry_angle = math.atan2(dy, dx)

    difference = abs(
        (text_angle - geometry_angle + math.pi / 2)
        % math.pi
        - math.pi / 2
    )

    return difference <= tolerance


# ==================================================
# Text normalization
# ==================================================

def normalize_text(text: str) -> str:

    for old, new in TEXT_REPLACEMENTS.items():
        text = text.replace(old, new)

    return text


# ==================================================
# Layer compatibility
# ==================================================

def calculate_layer_match_score(
    text_element: TextElement,
    geometry_element: GeometryElement,
) -> float:

    text = text_element.text
    entity_type = geometry_element.source.entity_type.upper()
    geometry_layer = geometry_element.source.layer

    if "%%C" in text:
        return 1.0 if entity_type in ("CIRCLE", "ARC") else 0.0

    if "开孔" in text:

        if "开孔" in geometry_layer:
            return 1.0

        return 0.5 if geometry_element.is_closed else 0.0

    coordinates = geometry_element.coordinates_3d

    if len(coordinates) != 2:
        return 0.0

    if not is_parallel(
        text_element.angle,
        coordinates[0],
        coordinates[1],
    ):
        return 0.0

    return (
        1.0
        if geometry_layer in ACCEPTED_LAYER_CANDIDATES
        else 0.5
    )


# ==================================================
# Geometry metadata
# ==================================================

def build_geometry_metadata(
    geometry_elements: list[GeometryElement],
    max_distance: float,
):

    geometry_info = []

    for geometry in geometry_elements:

        geometry_2d = geometry.geometry_2d

        centroid = None

        if geometry_2d is not None:
            try:
                centroid = geometry_2d.centroid
            except Exception:
                pass

        geometry_length = geometry.length or 0.0

        geometry_info.append({

            "valid": geometry.is_valid,

            "length": geometry_length,

            "type": geometry.source.entity_type.upper(),

            "layer": geometry.source.layer,

            "geometry_2d": geometry_2d,

            "centroid": centroid,

            "coordinates": geometry.coordinates_3d,

            "is_closed": geometry.is_closed,

            "max_distance": max(
                max_distance,
                geometry_length * 0.07,
                350,
            ),

            "angle": None,

        })

    return geometry_info


# ==================================================
# Distance calculator
# ==================================================

def create_distance_calculator(
    text_elements: list[TextElement],
    geometry_info: list[dict],
):

    text_count = len(text_elements)
    geometry_count = len(geometry_info)

    # -1 means distance has not been calculated.
    distance_cache = [
        [-1.0] * geometry_count
        for _ in range(text_count)
    ]

    def get_distance(
        text_index: int,
        geometry_index: int,
    ) -> float:

        cached = distance_cache[text_index][geometry_index]

        if cached >= 0:
            return cached

        text = text_elements[text_index]
        info = geometry_info[geometry_index]

        if text.bound_moved is None:
            return math.inf

        distances = []

        geometry_2d = info["geometry_2d"]

        if (
            geometry_2d is not None
            and len(info["coordinates"]) == 2
        ):

            try:
                distances.append(
                    text.bound_moved.distance(geometry_2d)
                )
            except Exception:
                pass

        centroid = info["centroid"]

        if (
            centroid is not None
            and (
                info["type"] in ("CIRCLE", "ARC")
                or info["is_closed"]
            )
        ):

            try:
                distances.append(
                    text.bound_moved.distance(centroid)
                )
            except Exception:
                pass

        result = min(distances) if distances else math.inf

        # Cache finite results and infinity separately.
        distance_cache[text_index][geometry_index] = (
            result if math.isfinite(result) else math.inf
        )

        return result

    return get_distance


# ==================================================
# Text filtering
# ==================================================

def get_valid_text_indices(
    text_elements: list[TextElement],
):

    return [
        i
        for i, text in enumerate(text_elements)
        if (
            text.bound_moved is not None
            and text.text.strip()
            and text.text.strip() != "UNKNOWN"
        )
    ]


# ==================================================
# Candidate selection
# ==================================================

def find_geometry_candidates(
    text_element: TextElement,
    text_index: int,
    geometry_elements: list[GeometryElement],
    geometry_info: list[dict],
    get_distance,
):

    candidates = []

    text_value = text_element.text

    is_diameter = "%%C" in text_value
    is_opening = "开孔" in text_value

    for geometry_index, geometry in enumerate(geometry_elements):

        info = geometry_info[geometry_index]

        if not info["valid"] or not info["length"]:
            continue

        # Cheap compatibility filtering before Shapely operations.
        if is_diameter:
            if info["type"] not in ("CIRCLE", "ARC"):
                continue

        elif is_opening:
            if "开孔" not in info["layer"] and not info["is_closed"]:
                continue

        elif len(info["coordinates"]) != 2:
            continue

        elif not is_parallel(
            text_element.angle,
            info["coordinates"][0],
            info["coordinates"][1],
        ):
            continue

        layer_score = calculate_layer_match_score(
            text_element,
            geometry,
        )

        if layer_score <= 0:
            continue

        distance = get_distance(
            text_index,
            geometry_index,
        )

        if distance > info["max_distance"]:
            continue

        candidates.append((
            -layer_score,
            distance,
            geometry_index,
            layer_score,
        ))

    candidates.sort(
        key=lambda item: (item[0], item[1])
    )

    return candidates


# ==================================================
# Caption assignment
# ==================================================

def append_caption(
    geometry: GeometryElement,
    text: str,
):

    current = geometry.caption

    if not current or current == "UNKNOWN":
        geometry.caption = text

    else:
        geometry.caption = current + ";" + text


def assign_candidate_captions(
    text_element: TextElement,
    candidates: list,
    geometry_elements: list[GeometryElement],
):

    text_value = text_element.text.strip()
    text_handle = text_element.source_handle

    for rank, candidate in enumerate(candidates):

        _, _, geometry_index, layer_score = candidate

        if rank > 0 and layer_score <= 0.5:
            break

        append_caption(
            geometry_elements[geometry_index],
            text_value,
        )
        geometry_elements[geometry_index].text_handle = text_handle


# ==================================================
# Caption measurement parsing
# ==================================================

def apply_diameter_measurement(
    geometry: GeometryElement,
    diameter: float,
):

    radius = diameter / 2

    geometry.radius_measured = radius

    if geometry.source.entity_type == "CIRCLE":

        geometry.length = round(math.pi * diameter)

        geometry.area = round(math.pi * radius * radius)

    elif geometry.source.entity_type == "ARC":

        if (
            geometry.start_angle is None
            or geometry.end_angle is None
        ):
            return

        sweep_degrees = (
            geometry.end_angle - geometry.start_angle
        ) % 360.0

        geometry.length = round(
            diameter * math.radians(sweep_degrees) / 2
        )

        geometry.area = round(
            sweep_degrees * diameter * diameter / 8
        )


def apply_opening_measurement(
    geometry: GeometryElement,
    width: float,
    height: float,
):

    if (
        geometry.source.entity_type == "LWPOLYLINE"
        and geometry.is_closed
    ):

        geometry.length = 2 * round(width + height)

        geometry.area = round(width * height)


def process_caption(
    geometry: GeometryElement,
):

    caption = geometry.caption or ""
    geometry.text = caption if caption!="UNKNOWN" else ""

    # Diameter annotation
    match = DIAMETER_PATTERN.search(caption)

    if match:

        geometry.caption = match.group(1)

        apply_diameter_measurement(
            geometry,
            float(match.group(2)),
        )

    # Opening annotation
    match = OPENING_PATTERN.search(geometry.caption)

    if match:

        geometry.caption = "开孔"

        apply_opening_measurement(
            geometry,
            float(match.group(1)),
            float(match.group(2)),
        )

    geometry.caption = normalize_text(
        geometry.caption
    )


# ==================================================
# Multiple caption resolution
# ==================================================

def resolve_multiple_captions(
    geometry_elements: list[GeometryElement],
    geometry_info: list[dict],
    text_elements: list[TextElement],
    valid_text_indices: list[int],
    get_distance,
):

    for geometry_index, geometry in enumerate(geometry_elements):

        caption = geometry.caption

        if not caption:
            continue

        if ";" in caption:

            info = geometry_info[geometry_index]

            coordinates = info["coordinates"]

            if len(coordinates) == 2:

                centroid = info["centroid"]

                if centroid is not None:

                    best_distance = math.inf
                    best_text = None
                    best_handle = ""

                    for text_index in valid_text_indices:

                        text = text_elements[text_index]

                        if not is_parallel(
                            text.angle,
                            coordinates[0],
                            coordinates[1],
                        ):
                            continue

                        boundary_distance = get_distance(
                            text_index,
                            geometry_index,
                        )

                        if boundary_distance > info["max_distance"]:
                            continue

                        if text.position_moved is None:
                            continue

                        centroid_distance = (
                            text.position_moved.distance(centroid)
                        )

                        combined_distance = (
                            boundary_distance * BOUND_DISTANCE_WEIGHT
                            + centroid_distance * CENTROID_DISTANCE_WEIGHT
                        )

                        if combined_distance < best_distance:

                            best_distance = combined_distance

                            best_text = text.text.strip()
                            best_handle = text.source_handle

                    if best_text is not None:
                        geometry.caption = best_text
                        geometry.text_handle = best_handle

        process_caption(geometry)


# ==================================================
# Main text assignment
# ==================================================

def assign_text_to_geometries(
    geometry_elements: list[GeometryElement],
    text_elements: list[TextElement],
    max_distance: float = 5.0,
) -> list[GeometryElement]:

    if not geometry_elements or not text_elements:
        return geometry_elements

    geometry_info = build_geometry_metadata(
        geometry_elements,
        max_distance,
    )

    get_distance = create_distance_calculator(
        text_elements,
        geometry_info,
    )

    valid_text_indices = get_valid_text_indices(
        text_elements
    )

    for text_index in valid_text_indices:

        text_element = text_elements[text_index]

        candidates = find_geometry_candidates(
            text_element=text_element,
            text_index=text_index,
            geometry_elements=geometry_elements,
            geometry_info=geometry_info,
            get_distance=get_distance,
        )

        if candidates:

            assign_candidate_captions(
                text_element,
                candidates,
                geometry_elements,
            )

    resolve_multiple_captions(
        geometry_elements=geometry_elements,
        geometry_info=geometry_info,
        text_elements=text_elements,
        valid_text_indices=valid_text_indices,
        get_distance=get_distance,
    )

    return geometry_elements
