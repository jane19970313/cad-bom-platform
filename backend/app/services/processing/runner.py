import json
import tempfile
import uuid
from io import BytesIO
from pathlib import Path
from typing import Any, Callable

from app.services.storage.factory import get_storage_service
from app.services.dxf_engine.pipeline import analyze_dxf


def run_dxf_pipeline(
    drawing_id,
    storage_key: str,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict:

    storage = get_storage_service()

    with tempfile.TemporaryDirectory(
        prefix="dxf_analysis_"
    ) as temp_dir:

        input_path = Path(temp_dir) / "input.dxf"

        # Copy the original drawing into temporary working storage.
        with storage.open(storage_key) as source:
            with input_path.open("wb") as destination:
                while chunk := source.read(1024 * 1024):
                    destination.write(chunk)

        # Run the DXF engine and forward actual stage events.
        result = analyze_dxf(
            dxf_path=str(input_path),
            progress_callback=progress_callback,
            # ai_graph_output_path="storage/training_graphs/drawing_001.pt",
            # ai_graph_options={
            #     "spatial_tolerance": 300.0,
            #     "dimension_tolerance": 2000.0,
            #     "text_tolerance": 300.0,
            # },
        )

    # Serialize the complete analysis result.
    result_json = json.dumps(
        result,
        ensure_ascii=False,
        allow_nan=False,
    )

    result_bytes = result_json.encode("utf-8")

    result_key = (
        f"drawings/{drawing_id}/analysis/{uuid.uuid4()}.json"
    )

    # Store the complete analysis artifact.
    storage.save(
        BytesIO(result_bytes),
        result_key,
    )

    return {
        "drawing_id": str(drawing_id),
        "result_storage_key": result_key,
        "summary": result.get("summary", {}),
        "engine_version": result.get("engine_version", "unknown"),
    }