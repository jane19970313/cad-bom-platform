from app.services.dxf_engine.geometry.geometry_helpers import (
    are_parallel,
    project_point_onto_axis,
    get_perpendicular_distance,
)


def project_dimensions(
    dimension_index,
    edge_start,
    edge_direction,
    parallel_tolerance=1e-3,
):
    """
    Project all parallel dimensions onto the target edge axis.

    Remove duplicate projected dimensions.

    Dimensions are not filtered by intersection with the target edge.
    This is important for subtraction calculations.
    """

    projected = {}

    for dimension in dimension_index:

        direction = dimension["direction"]

        if not are_parallel(
            direction,
            edge_direction,
            parallel_tolerance,
        ):
            continue

        start = project_point_onto_axis(
            dimension["start"],
            edge_start,
            edge_direction,
        )

        end = project_point_onto_axis(
            dimension["end"],
            edge_start,
            edge_direction,
        )

        low = min(start, end)
        high = max(start, end)

        line_distance = (
            get_perpendicular_distance(
                dimension["start"],
                edge_start,
                edge_direction,
            )
            + get_perpendicular_distance(
                dimension["end"],
                edge_start,
                edge_direction,
            )
        ) / 2

        record = {
            "start": low,
            "end": high,
            "length": dimension["length"],
            "line_distance": line_distance,
            "direction": direction,
        }

        # Rounded interval coordinates identify duplicate
        # projected dimensions.
        key = (
            round(low, 6),
            round(high, 6),
        )

        previous = projected.get(key)

        # Keep the dimension closest to the target edge.
        if (
            previous is None
            or line_distance < previous["line_distance"]
        ):
            projected[key] = record

    return list(projected.values())