from dataclasses import dataclass, field


@dataclass
class Classification:
    category: str
    engineering_type: str
    confidence: float
    status: str
    evidence: list[str] = field(default_factory=list)


@dataclass
class EngineeringElement:
    element_id: str
    classification: Classification

    source_handles: list[str] = field(default_factory=list)

    properties: dict = field(default_factory=dict)
    relationships: list[str] = field(default_factory=list)