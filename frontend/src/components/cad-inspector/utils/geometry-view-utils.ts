import type {
  GeometryElement,
  GeometryPoint,
} from "../types/geometry-view.types";

export interface GeometryBounds {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
  width: number;
  height: number;
}

export function getGeometryPoint(
  point: GeometryElement["coordinates_3d"][number]
): GeometryPoint {
  if (Array.isArray(point)) {
    return {
      x: Number(point[0]),
      y: Number(point[1]),
      z: Number(point[2] ?? 0),
    };
  }

  return {
    x: Number(point.x),
    y: Number(point.y),
    z: Number(point.z ?? 0),
  };
}

export function getGeometryBounds(
  elements: GeometryElement[]
): GeometryBounds {
  const coordinates = elements.flatMap((element) => {
    const points = element.coordinates_3d.map(
      getGeometryPoint
    );

    if (
      element.center &&
      element.radius &&
      element.radius > 0
    ) {
      const { x, y } = element.center;
      const r = element.radius;

      points.push(
        { x: x - r, y: y - r },
        { x: x + r, y: y + r }
      );
    }

    return points;
  });

  if (coordinates.length === 0) {
    return {
      minX: 0,
      minY: 0,
      maxX: 100,
      maxY: 100,
      width: 100,
      height: 100,
    };
  }

  const xs = coordinates.map((p) => p.x);
  const ys = coordinates.map((p) => p.y);

  const minX = Math.min(...xs);
  const minY = Math.min(...ys);
  const maxX = Math.max(...xs);
  const maxY = Math.max(...ys);

  return {
    minX,
    minY,
    maxX,
    maxY,
    width: Math.max(maxX - minX, 0.001),
    height: Math.max(maxY - minY, 0.001),
  };
}

export function getGeometryCaption(
  element: GeometryElement
): string {
  const caption = element.caption?.trim();

  if (
    !caption ||
    caption.toUpperCase() === "UNKNOWN"
  ) {
    return element.layer || "Unnamed geometry";
  }

  return caption;
}

export function getArcPath(
  cx: number,
  cy: number,
  radius: number,
  startAngle: number,
  endAngle: number
): string {
  const toRadians = (angle: number) =>
    (angle * Math.PI) / 180;

  const start = {
    x: cx + radius * Math.cos(toRadians(startAngle)),
    y: cy + radius * Math.sin(toRadians(startAngle)),
  };

  const end = {
    x: cx + radius * Math.cos(toRadians(endAngle)),
    y: cy + radius * Math.sin(toRadians(endAngle)),
  };

  let difference = (endAngle - startAngle) % 360;

  if (difference < 0) {
    difference += 360;
  }

  const largeArc = difference > 180 ? 1 : 0;

  return [
    `M ${start.x} ${start.y}`,
    `A ${radius} ${radius} 0 ${largeArc} 0 ${end.x} ${end.y}`,
  ].join(" ");
}