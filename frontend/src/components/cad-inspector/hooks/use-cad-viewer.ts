"use client";

import {
  useEffect,
  useRef,
  useState,
  type RefObject,
} from "react";

import type { AnalysisElement } from "@/types/analysis";
import type { HandleStats } from "../types/cad-viewer.types";

export function useCadViewer(
  dxfData: ArrayBuffer,
  elements: AnalysisElement[]
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const managerRef = useRef<any>(null);
  const previousHighlightRef = useRef<string[]>([]);

  const [viewerReady, setViewerReady] = useState(false);
  const [viewerError, setViewerError] =
    useState<string | null>(null);

  const [handleStats, setHandleStats] =
    useState<HandleStats>({
      total: 0,
      resolved: 0,
      missing: 0,
    });

  useEffect(() => {
    let cancelled = false;
    let manager: any = null;

    async function initializeViewer() {
      if (!containerRef.current) return;

      setViewerReady(false);
      setViewerError(null);

      setHandleStats({
        total: 0,
        resolved: 0,
        missing: 0,
      });

      previousHighlightRef.current = [];

      try {
        const cad = await import(
          "@mlightcad/cad-simple-viewer"
        );

        if (cancelled || !containerRef.current) return;

        manager = cad.AcApDocManager.createInstance({
          container: containerRef.current,
          width: containerRef.current.clientWidth || 1000,
          height: containerRef.current.clientHeight || 600,
          autoResize: true,
          useMainThreadDraw: true,
          preloadDefaultFonts: true,
        });

        if (!manager) {
          throw new Error(
            "Could not initialize the CAD viewer."
          );
        }

        managerRef.current = manager;

        const opened = await manager.openDocument(
          "uploaded-drawing.dxf",
          dxfData,
          {
            mode: 0,
            openViewMode: "extents",
          }
        );

        if (cancelled) return;

        if (!opened) {
          throw new Error(
            "The CAD viewer could not open this DXF file."
          );
        }

        const view = manager.curView;
        const database = manager.curDocument?.database;

        view?.zoomToFitDrawing(5000);

        if (!database) {
          throw new Error(
            "The drawing opened, but its CAD database was not available."
          );
        }

        let resolved = 0;
        let missing = 0;

        for (const element of elements) {
          const handle = String(
            element.source_handle ??
              element.handle ??
              ""
          ).trim();

          if (!handle) {
            missing++;
            continue;
          }

          const object =
            database.getObjectById(handle) ??
            database.getObjectById(handle.toUpperCase());

          if (object) {
            resolved++;
          } else {
            missing++;
          }
        }

        if (cancelled) return;

        setHandleStats({
          total: elements.length,
          resolved,
          missing,
        });

        setViewerReady(true);

        console.log("[CAD Viewer] Drawing opened.");
        console.log("[CAD Viewer] Handle mapping:", {
          total: elements.length,
          resolved,
          missing,
        });
      } catch (error) {
        if (cancelled) return;

        const message =
          error instanceof Error
            ? error.message
            : "Unknown CAD viewer error";

        setViewerError(message);

        console.error(
          "[CAD Viewer] Initialization failed:",
          error
        );
      }
    }

    void initializeViewer();

    return () => {
      cancelled = true;

      if (manager) {
        try {
          if (previousHighlightRef.current.length > 0) {
            manager.curView?.unhighlight(
              previousHighlightRef.current
            );
          }
        } catch (error) {
          console.warn(
            "[CAD Viewer] Could not clear highlight:",
            error
          );
        }

        if (managerRef.current === manager) {
          managerRef.current = null;
        }

        previousHighlightRef.current = [];

        void manager.destroy();
      }
    };
  }, [dxfData, elements]);

  return {
    containerRef,
    managerRef,
    previousHighlightRef,
    viewerReady,
    viewerError,
    handleStats,
  };
}