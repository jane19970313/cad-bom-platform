from pathlib import Path
import json

from app.services.dxf_engine.pipeline import analyze_dxf

DRAWING_IDX = 5

DXF_PATH = Path(f"test_drawings/{DRAWING_IDX}.dxf")


if not DXF_PATH.is_file():
    raise FileNotFoundError(
        f"Test drawing not found: {DXF_PATH}"
    )


result = analyze_dxf(
    str(DXF_PATH),
    flattening_distance=0.1,
    connectivity_tolerance=300.0,
    nearby_distance=0.0,
    ai_graph_output_path=f"storage/training_graphs/drawing_00{DRAWING_IDX}.pt",
    ai_graph_options={
        "spatial_tolerance": 300.0,
        "dimension_tolerance": 2000.0,
        "text_tolerance": 300.0,
        "connection_tolerance": 200.0,
        "angular_tolerance_degrees": 3.0,
        "collinear_tolerance": 20.0,
        "mirror_tolerance": 5.0,
        "tangent_tolerance_degrees": 12.0,
        "curvature_tolerance": 0.02,
        "relation_search_tolerance": 1500.0,
        "global_relation_max_neighbors": 24,
        "text_candidate_search_tolerance": 1500.0,
    },
)

# print("\nANALYSIS SUMMARY")
# print(json.dumps(result["summary"], indent=2))

# print("\nDRAWING INFORMATION")
# print(json.dumps(result["drawing"], indent=2))

# print("\nFIRST FIVE ELEMENTS")
# print(json.dumps(result["elements"][:5], indent=2))

output_path = Path("test_analysis_result.json")

output_path.write_text(
    json.dumps(
        result,
        indent=2,
        ensure_ascii=False,
        allow_nan=False,
    ),
    encoding="utf-8",
)

print(f"\nAnalysis saved to: {output_path.resolve()}")
