from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SourceReference:
    entity_handle: str
    entity_type: str
    layer: str
    layout: str
    block_path: tuple[str, ...] = ()


@dataclass
class RawEntity:
    source: SourceReference
    attributes: dict[str, Any] = field(default_factory=dict)
    text: str | None = None
    warnings: list[str] = field(default_factory=list)