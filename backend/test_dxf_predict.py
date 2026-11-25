from app.services.dxf_engine.ai_gnn.inference import predict_geometry
import torch
import json
from pathlib import Path
from datetime import datetime


# 1. Trained GNN model and semantic graph path
checkpoint_path = "storage/models/dxf_relation_aware_gnn_v8.pt"
semantic_graph_path = "storage/training_graphs/drawing_004.pt"

# 2. Load semantic graph
semantic_graph = torch.load(
    semantic_graph_path,
    map_location="cpu",
    weights_only=False
)

# 3. Geometry prediction
predictions = predict_geometry(
    semantic_graph,
    checkpoint_path
)

# 4. JSON output path
output_path = Path("storage/predictions/predictions_001.json")

# Create output directory if it does not exist
output_path.parent.mkdir(parents=True, exist_ok=True)

# 5. Prepare JSON data
result = {
    "metadata": {
        "checkpoint": checkpoint_path,
        "semantic_graph": semantic_graph_path,
        "prediction_count": len(predictions),
        "generated_at": datetime.now().astimezone().isoformat()
    },
    "predictions": predictions
}

# 6. Save predictions to JSON
with output_path.open("w", encoding="utf-8") as f:
    json.dump(
        result,
        f,
        ensure_ascii=False,
        indent=4,
        allow_nan=False
    )

print("=" * 60)
print("GNN inference completed")
print(f"Total geometries : {len(predictions)}")
print(f"JSON output      : {output_path}")
print("=" * 60)