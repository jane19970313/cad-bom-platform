import json
import csv
import os

# 1. JSON file reading
json_file = "test_analysis_result.json"

with open(json_file, "r", encoding="utf-8") as f:
    data = json.load(f)

# 2. geometry_elements extraction
geometry_elements = data.get("geometry_elements", [])

CSV_IDX = 1

# 3. CSV file generation
csv_file = f"storage/labels/labels_00{CSV_IDX}.csv"
csv_text_file = f"storage/labels/labels_text_00{CSV_IDX}.csv"

# Create directory if it does not exist
os.makedirs(os.path.dirname(csv_file), exist_ok=True)

with open(csv_file, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)

    # CSV header
    writer.writerow(["source_handle", "label", "length", "area", "radius"])

    #  entity_handle and layer extraction
    for entity in geometry_elements:

        handle = entity.get("source_handle")
        layer = entity.get("layer")
        length = entity.get("length")
        area = entity.get("area")
        radius = entity.get("radius")

        writer.writerow([handle, layer, length, area, radius])

with open(csv_text_file, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)

    # CSV header
    writer.writerow(["text_handle", "geometry_handle", "text", "relation_type", "is_match"])
    
    #  text_handle and geometry_handle extraction
    for entity in geometry_elements:
    
        geometry_handle = entity.get("source_handle")
        text_handle = entity.get("text_handle")
        text = entity.get("text")
        relation_type = "geometry_description_candidate"
        if "%%C" in text:
            relation_type = "dimension_value_candidate"
        is_match = 1

        if text_handle != "":
            writer.writerow([text_handle, geometry_handle, text, relation_type, is_match])

print(f"CSV file generation finished: {csv_file}")
print(f"extracted entities: {len(geometry_elements)}")