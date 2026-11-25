"use client";

import type { RefObject } from "react";

interface CadViewerCanvasProps {
  containerRef: RefObject<HTMLDivElement | null>;
  viewerReady: boolean;
  viewerError: string | null;
  onClear: () => void;
}

export function CadViewerCanvas({
  containerRef,
  viewerReady,
  viewerError,
  onClear,
}: CadViewerCanvasProps) {
  return (
    <section className="flex min-w-0 flex-col overflow-hidden rounded-xl border bg-background min-h-[65vh] xl:min-h-0">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold">
            Original DXF drawing
          </h2>

          <p className="text-xs text-muted-foreground">
            Select an extracted element to highlight its source object.
          </p>
        </div>

        <span
          className={`rounded-md px-2 py-1 text-xs ${
            viewerReady
              ? "bg-green-100 text-green-800"
              : "bg-muted text-muted-foreground"
          }`}
        >
          {viewerReady ? "Viewer ready" : "Loading viewer"}
        </span>
      </div>

      <div className="relative min-h-0 flex-1 overflow-hidden touch-none overscroll-none select-none">
        <div
          ref={containerRef}
          className="absolute inset-0 h-full w-full bg-white"
          onContextMenu={(event) => {
            event.preventDefault();
            onClear();
          }}
          onMouseDownCapture={(event) => {
            if (event.button === 1) {
              console.log(
                "[CAD Viewer] Middle mouse pressed"
              );
            }
          }}
        />

        {viewerError && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/95 p-6">
            <div className="max-w-lg text-center">
              <p className="font-semibold text-destructive">
                Could not load the drawing
              </p>

              <p className="mt-2 text-sm text-muted-foreground">
                {viewerError}
              </p>
            </div>
          </div>
        )}

        {!viewerReady && !viewerError && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/80">
            <p className="text-sm text-muted-foreground">
              Opening DXF drawing…
            </p>
          </div>
        )}
      </div>
    </section>
  );
}