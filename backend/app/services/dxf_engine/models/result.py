from dataclasses import dataclass, field
from typing import Any


@dataclass
class AnalysisResult:
    engine_version: str
    drawing_units: str | None

    raw_entity_count: int = 0
    geometry_element_count: int = 0
    engineering_element_count: int = 0

    elements: list[dict[str, Any]] = field(default_factory=list)
    relationships: list[dict[str, Any]] = field(default_factory=list)
    assemblies: list[dict[str, Any]] = field(default_factory=list)
    bom_candidates: list[dict[str, Any]] = field(default_factory=list)

    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)