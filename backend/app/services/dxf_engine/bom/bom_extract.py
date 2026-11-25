from app.services.dxf_engine.models.bom import BomElement

def extract_bom(elements) -> list[BomElement]:
    grouped = {}

    for element in elements:
        caption = element.get("caption")
        layer = element.get("layer") or "UNKNOWN"

        # Use layer when caption is UNKNOWN, None, or empty
        if not caption or caption.strip().upper() == "UNKNOWN":
            caption = layer

        key = caption

        if key not in grouped:
            grouped[key] = {
                "caption": caption,
                "length": 0.0,
                "area": 0.0,
                "count": 0,
                "source_handles": [],
            }

        item = grouped[key]

        item["length"] += element.get("length") or 0.0
        item["area"] += element.get("area") or 0.0
        item["count"] += 1

        source_handle = element.get("source_handle")
        if source_handle:
            item["source_handles"].append(source_handle)

    return [
        BomElement(
            caption=item["caption"],
            length=item["length"],
            area=item["area"],
            count=item["count"],
            material="",
            source_handles=item["source_handles"],
        )
        for item in grouped.values()
    ]