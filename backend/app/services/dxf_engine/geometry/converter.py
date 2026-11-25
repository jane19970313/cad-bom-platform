from app.services.dxf_engine.geometry.entity_converter import (
    convert_entity,
    should_convert_entity,
)

from app.services.dxf_engine.geometry.text_matcher import (
    assign_text_to_geometries,
)

from app.services.dxf_engine.geometry.measurement_calculator import (
    assign_measurements,
)

from app.services.dxf_engine.geometry.line_merger import (
    merge_connected_lines,
)

from app.services.dxf_engine.models.geometry import (
    GeometryElement,
    DimensionElement,
    TextElement,
)


def convert_geometry(
    modelspace_entities,
    scale: float,
    remove_handles: list[str],
    dimension_elements: list[DimensionElement],
    text_elements: list[TextElement],
    flattening_distance: float,
    diagnostics: list | None = None,
) -> list[GeometryElement]:
    """
    Convert DXF modelspace entities into GeometryElements.

    Processing steps:
        1. Filter removed entities.
        2. Convert supported DXF entities.
        3. Calculate geometry measurements.
        4. Assign text annotations.
        5. Report conversion failures.
    """

    geometry_elements = []
    conversion_failures = []

    removed_handles = set(remove_handles)

    # --------------------------------------------------
    # 1. Convert DXF entities
    # --------------------------------------------------

    for entity in modelspace_entities:

        handle = entity.dxf.handle

        if handle in removed_handles:
            continue        

        if not should_convert_entity(entity):
            continue

        geometry = convert_entity(
            entity,
            flattening_distance=flattening_distance,
            diagnostics=diagnostics,
        )

        if geometry is None:

            conversion_failures.append({
                "handle": handle,
                "type": entity.dxftype(),
                "reason": "Conversion failed",
            })

            continue

        geometry_elements.append(geometry)

    geometry_elements = merge_connected_lines(geometry_elements)

    # --------------------------------------------------
    # 2. Calculate measurements
    # --------------------------------------------------

    assign_measurements(
        geometry_elements=geometry_elements,
        dimension_elements=dimension_elements,
        scale=scale,
    )

    # --------------------------------------------------
    # 3. Assign text annotations
    # --------------------------------------------------

    assign_text_to_geometries(
        geometry_elements=geometry_elements,
        text_elements=text_elements,
    )

    # --------------------------------------------------
    # 4. Report conversion failures
    # --------------------------------------------------

    if diagnostics is not None:

        diagnostics.extend(
            f"Conversion failed: {failure}"
            for failure in conversion_failures
        )

    return geometry_elements