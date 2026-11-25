from collections import Counter
from pathlib import Path

import ezdxf


DXF_PATH = Path("test_drawings/sample.dxf")


def main():
    doc = ezdxf.readfile(DXF_PATH)

    modelspace = doc.modelspace()

    block_counts = Counter()
    block_entities = {}

    for insert in modelspace.query("INSERT"):
        block_name = insert.dxf.name
        block_counts[block_name] += 1

    print("\n" + "=" * 75)
    print("BLOCK INVENTORY")
    print("=" * 75)

    for block_name, reference_count in block_counts.most_common():

        print("\n" + "-" * 75)
        print(f"BLOCK NAME: {block_name}")
        print(f"REFERENCE COUNT: {reference_count}")

        if block_name not in doc.blocks:
            print("BLOCK DEFINITION NOT FOUND")
            continue

        block = doc.blocks[block_name]

        entity_counts = Counter()
        layers = Counter()

        for entity in block:
            entity_type = entity.dxftype()
            entity_counts[entity_type] += 1

            layer = entity.dxf.get("layer", "0")
            layers[layer] += 1

        block_entities[block_name] = {
            "entity_counts": entity_counts,
            "layers": layers,
        }

        print("\nENTITY TYPES:")

        for entity_type, count in entity_counts.most_common():
            print(f"  {entity_type:<25} {count:>6}")

        print("\nLAYERS:")

        for layer, count in layers.most_common():
            print(f"  {layer:<40} {count:>6}")

        print(f"\nTOTAL ENTITIES: {sum(entity_counts.values())}")

    print("\n" + "=" * 75)
    print("BLOCK INVENTORY COMPLETE")
    print("=" * 75)


if __name__ == "__main__":
    main()