from dataclasses import dataclass


@dataclass(frozen=True)
class EngineConfig:
    version: str = "0.1.0"

    # None means use the drawing's declared units where available.
    unit_override: str | None = None

    # Geometric tolerances are expressed in drawing units.
    connection_tolerance: float = 1.0
    duplicate_tolerance: float = 0.01
    spatial_tolerance: float = 1.0

    # Curve approximation tolerance, also in drawing units.
    curve_flattening_distance: float = 0.1

    include_modelspace: bool = True
    include_paperspace: bool = False
    expand_blocks: bool = True

    # Limits help prevent pathological or malicious input.
    max_entities: int = 1_000_000
    max_block_depth: int = 16