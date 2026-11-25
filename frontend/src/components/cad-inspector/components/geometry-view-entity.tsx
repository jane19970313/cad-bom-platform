"use client";

import type { GeometryElement } from "../types/geometry-view.types";

import {
  getGeometryCaption,
  getGeometryPoint,
  getArcPath,
} from "../utils/geometry-view-utils";

import { normalizeHandle } from "../utils/handle-utils";

interface GeometryViewEntityProps {
  element: GeometryElement;
  selectedHandle: string | null;
  onSelectHandle: (handle: string) => void;
  onHover: (element: GeometryElement | null) => void;
}

export function GeometryViewEntity({
  element,
  selectedHandle,
  onSelectHandle,
  onHover,
}: GeometryViewEntityProps) {
  const points = (element.coordinates_3d ?? [])
    .map(getGeometryPoint)
    .filter(
      (point) =>
        Number.isFinite(point.x) &&
        Number.isFinite(point.y)
    );

  const type = (element.geometry_type ?? "UNKNOWN").toUpperCase();

  const isSelected =
    normalizeHandle(element.source_handle) ===
    normalizeHandle(selectedHandle);

  const stroke = isSelected
    ? "#2563eb"
    : element.is_valid
      ? "#64748b"
      : "#ef4444";

  const commonProps = {
    stroke,
    strokeWidth: isSelected ? 2 : 1.2,
    vectorEffect: "non-scaling-stroke" as const,
    strokeLinejoin: "round" as const,
    strokeLinecap: "round" as const,
    fill: "none",
    strokeDasharray: element.is_valid
      ? undefined
      : "4 3",
  };

  const interactionProps = {
    onPointerEnter: () => onHover(element),
    onPointerLeave: () => onHover(null),
    onClick: (event: React.MouseEvent) => {
      event.stopPropagation();
      onSelectHandle(element.source_handle);
    },
    style: {
      cursor: "pointer",
    },
  };

  // Determine caption position.
  const anchor = (() => {
    if (element.center) {
      return {
        x: element.center.x,
        y: element.center.y,
      };
    }

    if (points.length > 0) {
      const middle = points[Math.floor(points.length / 2)];

      return {
        x: middle.x,
        y: middle.y,
      };
    }

    return null;
  })();

  const caption = getGeometryCaption(element);

  const labelColor = isSelected
    ? "#2563eb"
    : element.is_valid
      ? "#475569"
      : "#dc2626";

  const renderShape = () => {
    // Circle
    if (
      type.includes("CIRCLE") &&
      element.center &&
      element.radius != null
    ) {
      return (
        <g>
          <circle
            cx={element.center.x}
            cy={element.center.y}
            r={element.radius}
            {...commonProps}
            fill={
              isSelected
                ? "rgba(37,99,235,0.15)"
                : "none"
            }
          />

          <circle
            cx={element.center.x}
            cy={element.center.y}
            r={element.radius}
            stroke="transparent"
            strokeWidth={12}
            fill="none"
            vectorEffect="non-scaling-stroke"
            {...interactionProps}
          />
        </g>
      );
    }

    // Arc
    if (
      type.includes("ARC") &&
      element.center &&
      element.radius != null &&
      element.start_angle != null &&
      element.end_angle != null
    ) {
      const path = getArcPath(
        element.center.x,
        element.center.y,
        element.radius,
        element.start_angle,
        element.end_angle
      );

      return (
        <g>
          <path d={path} {...commonProps} />

          <path
            d={path}
            fill="none"
            stroke="transparent"
            strokeWidth={12}
            vectorEffect="non-scaling-stroke"
            {...interactionProps}
          />
        </g>
      );
    }

    // Lines, polylines and polygons
    if (points.length >= 2) {
      const coordinates = points
        .map((point) => `${point.x},${point.y}`)
        .join(" ");

      const isClosed =
        element.is_closed ||
        type.includes("POLYGON");

      return (
        <g>
          {isClosed ? (
            <polygon
              points={coordinates}
              {...commonProps}
              fill={
                isSelected
                  ? "rgba(37,99,235,0.18)"
                  : "rgba(100,116,139,0.08)"
              }
            />
          ) : (
            <polyline
              points={coordinates}
              {...commonProps}
            />
          )}

          <polyline
            points={coordinates}
            fill="none"
            stroke="transparent"
            strokeWidth={12}
            vectorEffect="non-scaling-stroke"
            {...interactionProps}
          />
        </g>
      );
    }

    // Single point
    if (points.length === 1) {
      return (
        <circle
          cx={points[0].x}
          cy={points[0].y}
          r={2}
          fill={stroke}
          {...interactionProps}
        />
      );
    }

    return null;
  };

  return (
    <g>
      {renderShape()}

      {/* Always-visible geometry caption */}
      {anchor && (
        <g
          pointerEvents="none"
          transform={`translate(${anchor.x}, ${anchor.y})`}
        >
          <text
            x={5}
            y={-6}
            fontSize={10}
            fontWeight={isSelected ? 700 : 500}
            fill={labelColor}
            stroke="white"
            strokeWidth={2.5}
            paintOrder="stroke"
            strokeLinejoin="round"
          >
            {caption}
          </text>

          {/* Additional information for selected geometry */}
          {isSelected && (
            <>
              <text
                x={5}
                y={8}
                fontSize={8}
                fill="#2563eb"
                stroke="white"
                strokeWidth={2}
                paintOrder="stroke"
              >
                {type}
              </text>

              <text
                x={5}
                y={19}
                fontSize={8}
                fill="#2563eb"
                stroke="white"
                strokeWidth={2}
                paintOrder="stroke"
              >
                {`L: ${element.length?.toFixed(2) ?? "—"} | A: ${element.area?.toFixed(2) ?? "—"}`}
              </text>
            </>
          )}
        </g>
      )}
    </g>
  );
}