import math

from app.services.dxf_engine.geometry.geometry_helpers import (
    get_unit_vector,
)

EPSILON = 1e-6

class DimensionIndex:

    __slots__ = ("records",)

    def __init__(self, dimension_elements):

        records = []

        for dimension in dimension_elements:

            try:
                if dimension.actual_length is None:
                    continue

                measured_length = float(dimension.actual_length)

                if (
                    not math.isfinite(measured_length)
                    or measured_length <= EPSILON
                ):
                    continue

                start, end = dimension.endpoints

                direction = get_unit_vector(start, end)

                if direction is None:
                    continue

                records.append({
                    "start": start,
                    "end": end,
                    "direction": direction,
                    "length": measured_length,
                })

            except (
                TypeError,
                ValueError,
                AttributeError,
                IndexError,
            ):
                continue

        self.records = tuple(records)

    def __len__(self):
        return len(self.records)

    def __iter__(self):
        return iter(self.records)