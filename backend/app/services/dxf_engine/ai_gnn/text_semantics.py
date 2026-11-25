from __future__ import annotations

import json
import re
from pathlib import Path

DEFAULT_CONFIG = Path(__file__).with_name("text_semantics.json")


def load_text_config(path=None):
    """Load drawing-specific CAD text rules without requiring an NLP package."""
    config_path = Path(path) if path else DEFAULT_CONFIG
    if not config_path.exists():
        return {}
    with config_path.open("r", encoding="utf-8") as stream:
        config = json.load(stream)
    if not isinstance(config, dict):
        raise ValueError("Text semantics configuration must be a JSON object.")
    return config


def normalize_text(content, config):
    """Apply ordered, user-editable CAD/OCR substitutions from JSON."""
    value = str(content or "")
    for rule in config.get("replacements", []):
        if rule.get("enabled", True) is False:
            continue
        pattern = str(rule.get("pattern", ""))
        if not pattern:
            continue
        flags = re.IGNORECASE if rule.get("ignore_case", False) else 0
        replacement = str(rule.get("replacement", ""))
        # JSON configuration uses the familiar $1/$2 capture syntax. Python's
        # re.sub expects \\g<1>, so translate numbered references and expand
        # them per match. This also keeps normal literal replacements intact.
        replacement = re.sub(
            r"\$(\d+)",
            lambda match: r"\g<" + match.group(1) + ">",
            replacement,
        )
        compiled = re.compile(pattern, flags=flags)
        value = compiled.sub(lambda match: match.expand(replacement), value)
    return value


def tokenize_text(content, config):
    """Tokenize Latin identifiers, CAD symbols, numbers, and Chinese text.

    jieba is optional. If it is not installed, deterministic character bigrams
    preserve useful Chinese subword evidence without adding a hard dependency.
    """
    value = normalize_text(content, config).lower()
    tokens = re.findall(
        r"%%c|%%d|%%p|[ø⌀φΦØ]|[a-z]+(?:[-_][a-z0-9]+)*|"
        r"[0-9]+(?:\.[0-9]+)?|[\u3400-\u9fff]+|[^\w\s]",
        value, flags=re.IGNORECASE,
    )
    options = config.get("chinese_tokenization", {})
    minimum_length = max(1, int(options.get("minimum_word_length", 1)))
    output = []
    for token in tokens:
        if re.search(r"[\u3400-\u9fff]", token):
            segmented = None
            if options.get("use_jieba", True):
                try:
                    import jieba
                    segmented = [
                        part.strip() for part in jieba.cut(token)
                        if part.strip() and len(part.strip()) >= minimum_length
                    ]
                except ImportError:
                    pass
            if segmented:
                output.extend(segmented)
            elif len(token) == 1:
                output.append(token)
            else:
                output.extend(
                    token[i:i + 2]
                    for i in range(len(token) - 1)
                    if len(token[i:i + 2]) >= minimum_length
                )
        elif len(token) >= minimum_length or not token.isalnum():
            output.append(token)
    return output


def classify_text(content, config):
    """Classify text with conservative precedence for general annotations.

    Annotation precedence is intentional: a load note containing a diameter,
    force, or length must not become a geometry measurement relationship.
    """
    normalized = normalize_text(content, config)
    patterns = config.get("category_patterns", {})
    for category in (
        "ANNOTATION", "TOLERANCE_GDT", "DIMENSION_VALUE",
        "PART_LABEL", "GEOMETRY_DESCRIPTION",
    ):
        for pattern in patterns.get(category, []):
            if re.search(pattern, normalized, flags=re.IGNORECASE):
                return category, normalized
    return "UNKNOWN", normalized



def classify_text_categories(content, config):
    """Return every semantic category matched by the text.

    A single annotation may contain both a geometry description and a
    dimension token (for example, '开孔%%C650'). Multi-label categories preserve
    both signals instead of forcing the text into one mutually-exclusive class.
    """
    normalized = normalize_text(content, config)
    patterns = config.get("category_patterns", {})
    ordered = (
        "ANNOTATION", "TOLERANCE_GDT", "DIMENSION_VALUE",
        "PART_LABEL", "GEOMETRY_DESCRIPTION",
    )
    categories = [
        category for category in ordered
        if any(
            re.search(pattern, normalized, flags=re.IGNORECASE)
            for pattern in patterns.get(category, [])
        )
    ]
    return (categories or ["UNKNOWN"]), normalized


def parse_measurement_evidence(content, config):
    """Extract diameter/radius values while retaining the normalized source."""
    normalized = normalize_text(content, config)
    diameter_pattern = config.get(
        "diameter_pattern",
        r"(?:%%c|[ø⌀ØΦφ])\s*([0-9]+(?:\.[0-9]+)?)",
    )
    radius_pattern = config.get(
        "radius_pattern", r"(?<![A-Z0-9])R\s*([0-9]+(?:\.[0-9]+)?)"
    )
    diameter = re.search(diameter_pattern, normalized, flags=re.IGNORECASE)
    radius = re.search(radius_pattern, normalized, flags=re.IGNORECASE)
    return {
        "normalized": normalized,
        "has_diameter_symbol": bool(diameter),
        "diameter_value": float(diameter.group(1)) if diameter else None,
        "has_radius_symbol": bool(radius),
        "radius_value": float(radius.group(1)) if radius else None,
    }
