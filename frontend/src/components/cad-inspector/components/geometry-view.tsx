
"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import type {
  GeometryElement,
  GeometryViewProps,
} from "../types/geometry-view.types";

import { getGeometryBounds } from "../utils/geometry-view-utils";
import { normalizeHandle } from "../utils/handle-utils";

import { GeometryViewEntity } from "./geometry-view-entity";

interface ViewBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface PointerPosition {
  x: number;
  y: number;
}

interface PointerState {
  start: PointerPosition;
  viewBox: ViewBox;
  pointerId: number;
  captureTarget: SVGElement;
  moved: boolean;
}

const MIN_ZOOM = 0.05;
const MAX_ZOOM = 100;
const ZOOM_FACTOR = 1.15;

function formatValue(value?: number | null): string {
  if (value == null || !Number.isFinite(value)) {
    return "—";
  }

  return Number(value.toFixed(3)).toLocaleString();
}

function getElementViewBox(
  element: GeometryElement
): ViewBox | null {
  const bounds = getGeometryBounds([element]);

  if (
    !Number.isFinite(bounds.minX) ||
    !Number.isFinite(bounds.maxX) ||
    !Number.isFinite(bounds.minY) ||
    !Number.isFinite(bounds.maxY)
  ) {
    return null;
  }

  const width = Math.max(bounds.width, 10);
  const height = Math.max(bounds.height, 10);

  const paddingX = width * 0.8 + 10;
  const paddingY = height * 0.8 + 10;

  return {
    x: bounds.minX - paddingX,
    y: -bounds.maxY - paddingY,
    width: width + paddingX * 2,
    height: height + paddingY * 2,
  };
}

export function GeometryView({
  elements,
  selectedHandle,
  onSelectHandle,
}: GeometryViewProps) {
  const drawingRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const pointerRef = useRef<PointerState | null>(null);

  const suppressClickRef = useRef(false);

  const previousSelectedRef = useRef<string | null>(null);

  const [hoveredElement, setHoveredElement] =
    useState<GeometryElement | null>(null);

  const [viewBox, setViewBox] = useState<ViewBox>({
    x: 0,
    y: 0,
    width: 1000,
    height: 700,
  });

  const [isInitialized, setIsInitialized] = useState(false);

  // --------------------------------------------------
  // Drawing bounds
  // --------------------------------------------------

  const bounds = useMemo(
    () => getGeometryBounds(elements),
    [elements]
  );

  const initialViewBox = useMemo(() => {
    const paddingX = bounds.width * 0.08 + 8;
    const paddingY = bounds.height * 0.08 + 8;

    return {
      x: bounds.minX - paddingX,
      y: -bounds.maxY - paddingY,
      width: Math.max(bounds.width + paddingX * 2, 20),
      height: Math.max(bounds.height + paddingY * 2, 20),
    };
  }, [bounds]);

  // --------------------------------------------------
  // Initial fit
  // --------------------------------------------------

  useEffect(() => {
    if (elements.length === 0) {
      setIsInitialized(false);
      return;
    }

    setViewBox(initialViewBox);
    setIsInitialized(true);

    previousSelectedRef.current = null;
  }, [initialViewBox, elements.length]);

  // --------------------------------------------------
  // Selected geometry
  // --------------------------------------------------

  const selectedElement = useMemo(() => {
    if (!selectedHandle) return null;

    const normalized = normalizeHandle(selectedHandle);

    return (
      elements.find(
        (element) =>
          normalizeHandle(element.source_handle) === normalized
      ) ?? null
    );
  }, [elements, selectedHandle]);

  // --------------------------------------------------
  // Focus geometry
  // --------------------------------------------------

  const focusElement = useCallback(
    (element: GeometryElement) => {
      const nextViewBox = getElementViewBox(element);

      if (nextViewBox) {
        setViewBox(nextViewBox);
      }
    },
    []
  );

  // --------------------------------------------------
  // Auto zoom when selection changes externally
  // --------------------------------------------------

  useEffect(() => {
    if (!selectedElement || !isInitialized) return;

    const normalized = normalizeHandle(
      selectedElement.source_handle
    );

    if (previousSelectedRef.current === normalized) {
      return;
    }

    previousSelectedRef.current = normalized;

    const selectedBounds = getGeometryBounds([
      selectedElement,
    ]);

    const minX = selectedBounds.minX;
    const maxX = selectedBounds.maxX;
    const minY = -selectedBounds.maxY;
    const maxY = -selectedBounds.minY;

    const isOutside =
      minX < viewBox.x ||
      maxX > viewBox.x + viewBox.width ||
      minY < viewBox.y ||
      maxY > viewBox.y + viewBox.height;

    if (isOutside) {
      focusElement(selectedElement);
    }
  }, [
    selectedElement,
    isInitialized,
    viewBox,
    focusElement,
  ]);

  // --------------------------------------------------
  // Zoom
  // --------------------------------------------------

  const zoom = useCallback(
    (factor: number, center?: PointerPosition) => {
      setViewBox((current) => {
        const width = current.width / factor;
        const height = current.height / factor;

        const nextWidth = Math.min(
          Math.max(
            width,
            initialViewBox.width / MAX_ZOOM
          ),
          initialViewBox.width / MIN_ZOOM
        );

        const nextHeight = Math.min(
          Math.max(
            height,
            initialViewBox.height / MAX_ZOOM
          ),
          initialViewBox.height / MIN_ZOOM
        );

        const ratioX = center
          ? (center.x - current.x) / current.width
          : 0.5;

        const ratioY = center
          ? (center.y - current.y) / current.height
          : 0.5;

        return {
          x: center
            ? center.x - ratioX * nextWidth
            : current.x + (current.width - nextWidth) / 2,

          y: center
            ? center.y - ratioY * nextHeight
            : current.y + (current.height - nextHeight) / 2,

          width: nextWidth,
          height: nextHeight,
        };
      });
    },
    [initialViewBox]
  );

  // --------------------------------------------------
  // Native wheel listener
  //
  // IMPORTANT:
  // passive: false allows preventDefault().
  // capture: true intercepts the event before parent
  // scroll handlers receive it.
  // --------------------------------------------------

  useEffect(() => {
    const container = drawingRef.current;

    if (!container) return;

    const handleNativeWheel = (event: WheelEvent) => {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      const svg = svgRef.current;

      if (!svg) return;

      const rect = svg.getBoundingClientRect();

      if (!rect.width || !rect.height) return;

      const xRatio =
        (event.clientX - rect.left) / rect.width;

      const yRatio =
        (event.clientY - rect.top) / rect.height;

      const center = {
        x: viewBox.x + xRatio * viewBox.width,
        y: viewBox.y + yRatio * viewBox.height,
      };

      const factor =
        event.deltaY < 0
          ? ZOOM_FACTOR
          : 1 / ZOOM_FACTOR;

      zoom(factor, center);
    };

    container.addEventListener(
      "wheel",
      handleNativeWheel,
      {
        passive: false,
        capture: true,
      }
    );

    return () => {
      container.removeEventListener(
        "wheel",
        handleNativeWheel,
        true
      );
    };
  }, [viewBox, zoom]);

  // --------------------------------------------------
  // Pan
  // --------------------------------------------------

  const handlePointerDown = useCallback(
    (event: React.PointerEvent<SVGSVGElement>) => {
      if (event.button !== 0) return;

      const target = event.target as Element;

      if (target.closest("[data-geometry-no-pan]")) {
        return;
      }

      const captureTarget = event.target as SVGElement;

      pointerRef.current = {
        start: {
          x: event.clientX,
          y: event.clientY,
        },
        viewBox: { ...viewBox },
        pointerId: event.pointerId,
        captureTarget,
        moved: false,
      };

      captureTarget.setPointerCapture(event.pointerId);
    },
    [viewBox]
  );

  const handlePointerMove = useCallback(
    (event: React.PointerEvent<SVGSVGElement>) => {
      const pointer = pointerRef.current;

      if (!pointer) return;

      if (event.pointerId !== pointer.pointerId) return;

      const rect = event.currentTarget.getBoundingClientRect();

      if (!rect.width || !rect.height) return;

      const dx = event.clientX - pointer.start.x;
      const dy = event.clientY - pointer.start.y;

      if (
        Math.abs(dx) > 3 ||
        Math.abs(dy) > 3
      ) {
        pointer.moved = true;
      }

      if (!pointer.moved) return;

      const scaleX =
        pointer.viewBox.width / rect.width;

      const scaleY =
        pointer.viewBox.height / rect.height;

      setViewBox({
        ...pointer.viewBox,
        x: pointer.viewBox.x - dx * scaleX,
        y: pointer.viewBox.y - dy * scaleY,
      });
    },
    []
  );

  const handlePointerUp = useCallback(
    (event: React.PointerEvent<SVGSVGElement>) => {
      const pointer = pointerRef.current;

      if (!pointer) return;

      if (event.pointerId !== pointer.pointerId) return;

      if (pointer.moved) {
        suppressClickRef.current = true;

        requestAnimationFrame(() => {
          suppressClickRef.current = false;
        });
      }

      pointerRef.current = null;

      if (
        event.currentTarget.hasPointerCapture(
          event.pointerId
        )
      ) {
        pointer.captureTarget.releasePointerCapture(pointer.pointerId);
      }
    },
    []
  );

  // --------------------------------------------------
  // Selection
  // --------------------------------------------------

  const handleSelect = useCallback(
    (handle: string) => {
      if (suppressClickRef.current) return;

      onSelectHandle(handle);
    },
    [onSelectHandle]
  );

  // --------------------------------------------------
  // Render
  // --------------------------------------------------

  return (
    <section className="cad-inspector-result-panel flex min-h-[420px] flex-col overflow-hidden rounded-xl border">

      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3">
        <div>
          <h4 className="text-sm font-semibold">
            Geometry Visualization
          </h4>

          <p className="text-xs text-muted-foreground">
            Extracted CAD geometry
          </p>
        </div>

        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <span>{elements.length} elements</span>

          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-blue-600" />
            Selected
          </span>
        </div>
      </div>

      {/* Toolbar */}
      <div className="flex items-center justify-between border-b px-3 py-2">
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => zoom(1.25)}
            className="rounded-md border px-3 py-1 text-sm hover:bg-muted"
            title="Zoom in"
          >
            +
          </button>

          <button
            type="button"
            onClick={() => zoom(1 / 1.25)}
            className="rounded-md border px-3 py-1 text-sm hover:bg-muted"
            title="Zoom out"
          >
            −
          </button>

          <button
            type="button"
            onClick={() => setViewBox(initialViewBox)}
            className="rounded-md border px-3 py-1 text-xs hover:bg-muted"
          >
            Fit drawing
          </button>

          <button
            type="button"
            disabled={!selectedElement}
            onClick={() => {
              if (!selectedElement) return;

              focusElement(selectedElement);
            }}
            className="rounded-md border px-3 py-1 text-xs hover:bg-muted disabled:opacity-40"
          >
            Focus selected
          </button>
        </div>

        <span className="text-xs text-muted-foreground">
          Scroll to zoom · Drag to move
        </span>
      </div>

      {/* Drawing */}
      <div
        ref={drawingRef}
        className="cad-inspector-geometry-canvas relative min-h-[350px] flex-1 overflow-hidden overscroll-none touch-none"
        style={{
          overscrollBehavior: "none",
          touchAction: "none",
        }}
      >
        {elements.length === 0 ? (
          <div className="flex min-h-[350px] items-center justify-center text-sm text-muted-foreground">
            No geometry elements available.
          </div>
        ) : (
          <svg
            ref={svgRef}
            viewBox={`${viewBox.x} ${viewBox.y} ${viewBox.width} ${viewBox.height}`}
            preserveAspectRatio="xMidYMid meet"
            className="h-full min-h-[350px] w-full touch-none select-none"
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
            onPointerCancel={handlePointerUp}
            onLostPointerCapture={() => {
              pointerRef.current = null;
            }}
            style={{
              cursor: pointerRef.current
                ? "grabbing"
                : "grab",
            }}
          >
            <g transform="scale(1,-1)">
              {elements.map((element) => (
                <GeometryViewEntity
                  key={element.element_id}
                  element={element}
                  selectedHandle={selectedHandle}
                  onSelectHandle={handleSelect}
                  onHover={setHoveredElement}
                />
              ))}
            </g>
          </svg>
        )}

        {/* Hover information */}
        {hoveredElement &&
          normalizeHandle(hoveredElement.source_handle) !==
            normalizeHandle(selectedHandle) && (
            <div className="pointer-events-none absolute left-3 top-3 z-10 w-64 rounded-lg border bg-background/95 p-3 shadow-lg backdrop-blur">
              <p className="truncate text-sm font-semibold">
                {hoveredElement.caption === "UNKNOWN"
                  ? hoveredElement.layer
                  : hoveredElement.caption}
              </p>

              <p className="mt-1 text-xs text-muted-foreground">
                {hoveredElement.geometry_type}
              </p>

              <div className="mt-3 space-y-2 text-xs">
                <div className="flex justify-between gap-3">
                  <span className="text-muted-foreground">
                    Layer
                  </span>

                  <span className="max-w-36 truncate font-medium">
                    {hoveredElement.layer || "—"}
                  </span>
                </div>

                <div className="flex justify-between">
                  <span className="text-muted-foreground">
                    Length
                  </span>

                  <span className="font-medium">
                    {formatValue(hoveredElement.length)}
                  </span>
                </div>

                <div className="flex justify-between">
                  <span className="text-muted-foreground">
                    Area
                  </span>

                  <span className="font-medium">
                    {formatValue(hoveredElement.area)}
                  </span>
                </div>

                <div className="flex justify-between gap-3">
                  <span className="text-muted-foreground">
                    Handle
                  </span>

                  <span className="font-mono">
                    {hoveredElement.source_handle}
                  </span>
                </div>
              </div>
            </div>
          )}

        {/* Instructions */}
        <div className="pointer-events-none absolute bottom-3 left-3 rounded-md border bg-background/90 px-3 py-2 text-xs text-muted-foreground">
          Click to select · Hover for properties · Drag to pan
        </div>
      </div>
    </section>
  );
}
