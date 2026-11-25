from dataclasses import dataclass, field


@dataclass
class ClassificationResult:
    engineering_type: str
    confidence: float
    status: str
    evidence: list[str] = field(default_factory=list)


def classify_element(element, nearby_elements=None):
    nearby_elements = nearby_elements or []

    evidence = []

    layer = element.source.layer.upper()
    entity_type = element.source.entity_type
    geometry_type = element.geometry_type

    # Layer names provide clues, not proof.
    if "PLATE" in layer and geometry_type == "CLOSED_PROFILE":
        evidence.extend([
            "PLATE_LAYER",
            "CLOSED_PROFILE",
        ])

        return ClassificationResult(
            engineering_type="PLATE_CANDIDATE",
            confidence=0.65,
            status="candidate",
            evidence=evidence,
        )

    if "BEAM" in layer or "COLUMN" in layer:
        evidence.append("STRUCTURAL_MEMBER_LAYER")

        return ClassificationResult(
            engineering_type="MEMBER_CANDIDATE",
            confidence=0.65,
            status="candidate",
            evidence=evidence,
        )

    if entity_type == "CIRCLE":
        evidence.append("CIRCULAR_GEOMETRY")

        return ClassificationResult(
            engineering_type="CIRCULAR_FEATURE",
            confidence=0.40,
            status="ambiguous",
            evidence=evidence,
        )

    if geometry_type == "CLOSED_PROFILE":
        evidence.append("CLOSED_GEOMETRY")

        return ClassificationResult(
            engineering_type="CLOSED_PROFILE_CANDIDATE",
            confidence=0.35,
            status="unclassified",
            evidence=evidence,
        )

    return ClassificationResult(
        engineering_type="UNCLASSIFIED",
        confidence=0.0,
        status="unclassified",
        evidence=[],
    )
