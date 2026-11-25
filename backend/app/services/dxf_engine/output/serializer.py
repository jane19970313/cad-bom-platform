import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def json_safe(value: Any):
    if is_dataclass(value):
        return json_safe(asdict(value))

    if isinstance(value, dict):
        return {
            str(key): json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]

    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()

    if hasattr(value, "item"):
        return value.item()

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    return str(value)


def save_result_json(result: dict, path: str | Path):
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    temporary = output.with_suffix(output.suffix + ".tmp")

    with temporary.open("w", encoding="utf-8") as file:
        json.dump(
            json_safe(result),
            file,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )

    temporary.replace(output)