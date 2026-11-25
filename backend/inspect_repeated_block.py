from pathlib import Path

import ezdxf


DXF_PATH = Path("test_drawings/sample.dxf")
TARGET_BLOCK = "B202623154052"


def main():
    doc = ezdxf.readfile(DXF_PATH)
    block = doc.blocks.get(TARGET_BLOCK)

    if block is None:
        print(f"Block not found: {TARGET_BLOCK}")
        return

    print("=" * 75)
    print("BLOCK DEFINITION")
    print("=" * 75)

    print("Name:", block.name)
    print("Base point:", tuple(block.block.dxf.base_point))

    print("\nBLOCK GEOMETRY")

    for index, entity in enumerate(block):
        entity_type = entity.dxftype()

        print(f"\nEntity {index + 1}")
        print("Type:", entity_type)
        print("Handle:", entity.dxf.get("handle"))
        print("Layer:", entity.dxf.get("layer", "0"))

        if entity_type == "LWPOLYLINE":
            points = list(entity.get_points("xyb"))

            print("Closed:", entity.closed)
            print("Elevation:", entity.dxf.get("elevation", 0))
            print("Vertex count:", len(points))
            print("Vertices (x, y, bulge):")

            for point in points:
                print(
                    f"  X={point[0]:.4f}, "
                    f"Y={point[1]:.4f}, "
                    f"Bulge={point[2]:.6f}"
                )

            if points:
                xs = [point[0] for point in points]
                ys = [point[1] for point in points]

                print(
                    "Local bounding box:",
                    (
                        min(xs),
                        min(ys),
                        max(xs),
                        max(ys),
                    ),
                )

    print("\n" + "=" * 75)
    print("INSERT REFERENCES")
    print("=" * 75)

    modelspace = doc.modelspace()

    inserts = [
        insert
        for insert in modelspace.query("INSERT")
        if insert.dxf.name == TARGET_BLOCK
    ]

    print("Reference count:", len(inserts))

    for index, insert in enumerate(inserts, start=1):
        print(f"\nReference {index}")
        print("Handle:", insert.dxf.handle)
        print("Insertion point:", tuple(insert.dxf.insert))
        print("Rotation:", insert.dxf.get("rotation", 0.0))
        print("X scale:", insert.dxf.get("xscale", 1.0))
        print("Y scale:", insert.dxf.get("yscale", 1.0))
        print("Z scale:", insert.dxf.get("zscale", 1.0))
        print("Column count:", insert.dxf.get("column_count", 1))
        print("Row count:", insert.dxf.get("row_count", 1))

    print("\nInspection complete.")


if __name__ == "__main__":
    main()
