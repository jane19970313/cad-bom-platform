from dataclasses import dataclass, field


@dataclass
class BomElement:
    caption: str
    count: int
    material: str

    length: float = 0.0
    area: float = 0.0
    volume: float = 0.0
    mass: float = 0.0

    source_handles: list[str] = field(default_factory=list)