from dataclasses import dataclass
from pathlib import Path

import ezdxf


@dataclass
class DXFDocument:
    document: object
    path: str
    version: str
    units_code: int
    units_name: str | None
    warnings: list[str]


UNIT_NAMES = {
    0: "unitless",
    1: "inches",
    2: "feet",
    4: "millimeters",
    5: "centimeters",
    6: "meters",
    7: "kilometers",
}

def get_dxf_scale_info(document):
    header = document.header

    return {
        "insunits": header.get("$INSUNITS", 0),
        "dimscale": header.get("$DIMSCALE", 1.0),
        "dimlfac": header.get("$DIMLFAC", 1.0),
        "ltscale": header.get("$LTSCALE", 1.0),
        "measurement": header.get("$MEASUREMENT", 0),
    }

def open_dxf(path: str | Path) -> DXFDocument:
    file_path = Path(path)

    if not file_path.is_file():
        raise FileNotFoundError(f"DXF file not found: {file_path}")

    warnings = []

    try:
        document = ezdxf.readfile(file_path)
    except ezdxf.DXFError as exc:
        raise ValueError(f"Unable to read DXF: {exc}") from exc

    units_code = int(document.header.get("$INSUNITS", 0))
    units_name = UNIT_NAMES.get(units_code)

    scale_info = get_dxf_scale_info(document)
    print(f"[DEBUG] scale info: {scale_info}", flush=True)

    if units_code == 0:
        warnings.append(
            "Drawing units are unspecified. "
            "Measurements must not be interpreted as physical units "
            "until units are confirmed."
        )

    return DXFDocument(
        document=document,
        path=str(file_path),
        version=document.dxfversion,
        units_code=units_code,
        units_name=units_name,
        warnings=warnings,
    )