import { AcGeBox2d } from "@mlightcad/geometry-engine";

export function getEntityZoomBox(
  object: any,
  manager: any
): AcGeBox2d | null {
  try {
    const extents = object?.geometricExtents;

    if (!extents || extents.isEmpty?.()) {
      return null;
    }

    const min = extents.min;
    const max = extents.max;

    if (
      !Number.isFinite(min?.x) ||
      !Number.isFinite(min?.y) ||
      !Number.isFinite(max?.x) ||
      !Number.isFinite(max?.y)
    ) {
      return null;
    }

    const box = new AcGeBox2d(
      { x: min.x, y: min.y },
      { x: max.x, y: max.y }
    );

    const drawingSize =
      manager?.curView?.getDrawingExtents?.()?.size;

    const drawingScale = drawingSize
      ? Math.max(drawingSize.x, drawingSize.y)
      : 1000;

    box.expandByScalar(drawingScale * 0.15);

    return box;
  } catch (error) {
    console.warn(
      "[CAD Viewer] Could not calculate entity bounds:",
      error
    );

    return null;
  }
}