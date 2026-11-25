import json
from collections import Counter
from pathlib import Path


RESULT_PATH = Path("test_analysis_result.json")

with RESULT_PATH.open("r", encoding="utf-8") as file:
    result = json.load(file)


raw_entities = result.get("raw_entities", [])
elements = result.get("elements", [])


def print_counter(title, counter, limit=30):
    print(f"\n{'=' * 65}")
    print(title)
    print("=" * 65)

    for name, count in counter.most_common(limit):
        print(f"{name:<40} {count:>8}")

    print(f"\nTotal distinct entries: {len(counter)}")


# Raw DXF entity types.
entity_types = Counter(
    item["source"]["entity_type"]
    for item in raw_entities
)

# Raw DXF layers.
raw_layers = Counter(
    item["source"]["layer"]
    for item in raw_entities
)

# Converted geometry types.
geometry_types = Counter(
    item["geometry_type"]
    for item in elements
)

# Geometry elements grouped by original DXF layer.
geometry_layers = Counter(
    item["layer"]
    for item in elements
)

# Block INSERT references.
insert_entities = [
    item for item in raw_entities
    if item["source"]["entity_type"] == "INSERT"
]

block_names = Counter(
    item["attributes"].get("block_name", "UNKNOWN")
    for item in insert_entities
)

# Annotation entity types.
annotation_types = {
    "TEXT",
    "MTEXT",
    "ATTRIB",
    "ATTDEF",
    "DIMENSION",
    "LEADER",
    "MLEADER",
}

annotations = Counter({
    entity_type: count
    for entity_type, count in entity_types.items()
    if entity_type in annotation_types
})

# Compare raw entity handles against converted geometry handles.
geometry_handles = {
    item["source_handle"]
    for item in elements
}

not_converted = [
    item for item in raw_entities
    if item["source"]["entity_handle"] not in geometry_handles
]

not_converted_types = Counter(
    item["source"]["entity_type"]
    for item in not_converted
)

print("\nDXF DRAWING INVENTORY")

print_counter("RAW ENTITY TYPES", entity_types)
print_counter("RAW ENTITY LAYERS", raw_layers)
print_counter("CONVERTED GEOMETRY TYPES", geometry_types)
print_counter("GEOMETRY BY LAYER", geometry_layers)
print_counter("ANNOTATION TYPES", annotations)
print_counter("ENTITIES NOT CONVERTED TO GEOMETRY", not_converted_types)
print_counter("BLOCK INSERT REFERENCES", block_names)

print("\n" + "=" * 65)
print("TOTALS")
print("=" * 65)

print(f"Raw entities:                  {len(raw_entities)}")
print(f"Converted geometry elements:   {len(elements)}")
print(f"Entities without geometry:     {len(not_converted)}")
print(f"Block INSERT references:       {len(insert_entities)}")
print(f"Annotation entities:           {sum(annotations.values())}")
