"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import type { AnalysisElement } from "@/types/analysis";

import type {
  CadViewerProps,
  PipelineStep,
  StageProps,
} from "./types/cad-viewer.types";

import { CadViewerHeader } from "./components/cad-viewer-header";
import { CadViewerCanvas } from "./components/cad-viewer-canvas";
import { CadViewerSidebar } from "./components/cad-viewer-sidebar";

import { useCadViewer } from "./hooks/use-cad-viewer";
import { useCadSelection } from "./hooks/use-cad-selection";
import { useCadMonochrome } from "./hooks/use-cad-monochrome";

import { getEntityZoomBox } from "./utils/cad-geometry-utils";
import {
  getNodeHandle,
  normalizeHandle,
} from "./utils/handle-utils";

const EMPTY_ELEMENTS: AnalysisElement[] = [];

export function CadViewer({
  dxfData,
  analysis,
}: CadViewerProps) {
  const elements = analysis.elements ?? EMPTY_ELEMENTS;

  const [activeStep, setActiveStep] =
    useState<PipelineStep>(1);

  const activeStepRef = useRef<PipelineStep>(1);

  const pipelineContentRef =
    useRef<HTMLDivElement>(null);

  const [search, setSearch] = useState("");

  useEffect(() => {
    activeStepRef.current = activeStep;
  }, [activeStep]);

  const {
    containerRef,
    managerRef,
    previousHighlightRef,
    viewerReady,
    viewerError,
    handleStats,
  } = useCadViewer(dxfData, elements);

  const selection = useCadSelection(elements);

  const {
    selectedElement,
    setSelectedElement,
    selectedHandle,
    setSelectedHandle,
    selectedConnectivityNode,
    setSelectedConnectivityNode,
    selectionMessage,
    setSelectionMessage,
    findElement,
    reset: resetSelection,
  } = selection;

  const {
    monochrome,
    toggleMonochrome,
  } = useCadMonochrome(managerRef);

  // --------------------------------------------------
  // Select CAD entity
  // --------------------------------------------------

  const selectHandle = useCallback(
    (
      rawHandle: unknown,
      sourceElement?: AnalysisElement | null,
      shouldZoom = true
    ) => {
      const handle = normalizeHandle(rawHandle);

      if (!handle) {
        setSelectionMessage(
          "This item does not contain a DXF handle."
        );

        return;
      }

      setSelectedHandle(handle);

      // Preserve the classified element if available.
      const matchedElement =
        sourceElement ?? findElement(handle);

      setSelectedElement(matchedElement);

      // Match connectivity node.
      const connectivityNodes =
        analysis.connectivity_nodes ?? [];

      const matchedNode = connectivityNodes.find(
        (node: any) => {
          if (typeof node !== "string") {
            return (
              normalizeHandle(getNodeHandle(node)) === handle
            );
          }

          const parts = node.split("'");

          return (
            normalizeHandle(parts[3]) === handle
          );
        }
      );

      setSelectedConnectivityNode(
        matchedNode
          ? getNodeHandle(matchedNode)
          : null
      );

      const manager = managerRef.current;
      const view = manager?.curView;
      const database = manager?.curDocument?.database;

      if (!view || !database) {
        setSelectionMessage(
          "The CAD viewer is not ready."
        );

        return;
      }

      // Clear previous highlight.
      if (previousHighlightRef.current.length > 0) {
        try {
          view.unhighlight(
            previousHighlightRef.current
          );
        } catch (error) {
          console.warn(
            "[CAD Viewer] Could not clear previous highlight:",
            error
          );
        }

        previousHighlightRef.current = [];
      }

      // Resolve handle against CAD database.
      const object =
        database.getObjectById(handle) ??
        database.getObjectById(handle.toLowerCase()) ??
        database.getObjectById(handle.toUpperCase());

      if (!object) {
        setSelectionMessage(
          `DXF handle ${handle} could not be resolved in the drawing database.`
        );

        console.warn(
          "[CAD Viewer] Unresolved handle:",
          handle
        );

        return;
      }

      const objectId = object.objectId;

      // Highlight entity.
      view.highlight([objectId]);

      previousHighlightRef.current = [objectId];

      // Only inspector selections should zoom.
      if (shouldZoom) {
        const zoomBox = getEntityZoomBox(
          object,
          manager
        );

        if (zoomBox) {
          view.zoomTo(zoomBox, 0.6);
        }
      }

      setSelectionMessage(
        shouldZoom
          ? `Highlighted and centered DXF object ${handle}.`
          : `Highlighted DXF object ${handle}.`
      );

      console.log(
        "[CAD Viewer] Selected entity:",
        {
          handle,
          objectId,
          step: activeStepRef.current,
          element: matchedElement,
        }
      );
    },
    [
      analysis.connectivity_nodes,
      findElement,
      managerRef,
      previousHighlightRef,
      setSelectedElement,
      setSelectedHandle,
      setSelectedConnectivityNode,
      setSelectionMessage,
    ]
  );

  // --------------------------------------------------
  // Clear selection
  // --------------------------------------------------

  const clearSelection = useCallback(() => {
    const manager = managerRef.current;
    const view = manager?.curView;

    if (view) {
      try {
        view.selectionSet.clear();

        if (previousHighlightRef.current.length > 0) {
          view.unhighlight(
            previousHighlightRef.current
          );
        }
      } catch (error) {
        console.warn(
          "[CAD Viewer] Could not clear selection:",
          error
        );
      }
    }

    previousHighlightRef.current = [];

    resetSelection("Selection cleared.");
  }, [
    managerRef,
    previousHighlightRef,
    resetSelection,
  ]);

  // --------------------------------------------------
  // Connectivity node selection
  // --------------------------------------------------

  const selectNode = useCallback(
    (handle: string) => {
      setSelectedConnectivityNode(handle);

      selectHandle(handle);
    },
    [
      selectHandle,
      setSelectedConnectivityNode,
    ]
  );

  // --------------------------------------------------
  // Listen to selections from original DXF viewer
  // --------------------------------------------------

  useEffect(() => {
    if (!viewerReady) return;

    const manager = managerRef.current;

    const selectionSet =
      manager?.curView?.selectionSet;

    if (!manager || !selectionSet) return;

    // Entity selected inside drawing.
    const handleSelectionAdded = (
      args: { ids: string[] }
    ) => {
      const selectedId =
        args.ids?.[args.ids.length - 1];

      if (!selectedId) return;

      const matchedElement =
        elements.find(
          (element) =>
            normalizeHandle(
              element.source_handle ?? element.handle
            ) === normalizeHandle(selectedId)
        ) ?? null;

      setSearch("");

      // Drawing selection should not zoom.
      selectHandle(
        selectedId,
        matchedElement,
        false
      );
    };

    // Entity deselected inside drawing.
    const handleSelectionRemoved = () => {
      const remainingIds =
        selectionSet.ids ?? [];

      if (remainingIds.length === 0) {
        if (previousHighlightRef.current.length > 0) {
          try {
            manager.curView?.unhighlight(
              previousHighlightRef.current
            );
          } catch (error) {
            console.warn(
              "[CAD Viewer] Could not clear highlight:",
              error
            );
          }
        }

        previousHighlightRef.current = [];

        resetSelection("Selection cleared.");

        return;
      }

      const selectedId =
        remainingIds[remainingIds.length - 1];

      const matchedElement =
        elements.find(
          (element) =>
            normalizeHandle(
              element.source_handle ?? element.handle
            ) === normalizeHandle(selectedId)
        ) ?? null;

      selectHandle(
        selectedId,
        matchedElement,
        false
      );
    };

    selectionSet.events.selectionAdded.addEventListener(
      handleSelectionAdded
    );

    selectionSet.events.selectionRemoved.addEventListener(
      handleSelectionRemoved
    );

    return () => {
      selectionSet.events.selectionAdded.removeEventListener(
        handleSelectionAdded
      );

      selectionSet.events.selectionRemoved.removeEventListener(
        handleSelectionRemoved
      );
    };
  }, [
    viewerReady,
    managerRef,
    elements,
    selectHandle,
    resetSelection,
    previousHighlightRef,
  ]);

  // --------------------------------------------------
  // Scroll selected entity into view
  // --------------------------------------------------

  useEffect(() => {
    if (!selectedHandle) return;

    const normalized =
      normalizeHandle(selectedHandle);

    const frame = requestAnimationFrame(() => {
      const container =
        pipelineContentRef.current;

      if (!container) return;

      const matchingRow = container.querySelector(
        `[data-pipeline-handle="${normalized}"]`
      );

      const target =
        matchingRow ??
        container.querySelector(
          "#selected-entity-card"
        );

      target?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    });

    return () => {
      cancelAnimationFrame(frame);
    };
  }, [selectedHandle, activeStep]);

  // --------------------------------------------------
  // Pipeline stage props
  // --------------------------------------------------

  const stageProps: StageProps = useMemo(
    () => ({
      analysis,

      selectedHandle,
      selectedElement,
      selectedConnectivityNode,

      selectionMessage,

      viewerReady,
      handleStats,

      search,
      setSearch,

      onSelectHandle: selectHandle,
      onSelectNode: selectNode,
    }),
    [
      analysis,
      selectedHandle,
      selectedElement,
      selectedConnectivityNode,
      selectionMessage,
      viewerReady,
      handleStats,
      search,
      selectHandle,
      selectNode,
    ]
  );

  // --------------------------------------------------
  // Render
  // --------------------------------------------------

  return (
    <div className="flex w-full flex-col gap-0">

      {/* Header and pipeline navigation */}
      <CadViewerHeader
        activeStep={activeStep}
        setActiveStep={setActiveStep}
        viewerReady={viewerReady}
        monochrome={monochrome}
        onClear={clearSelection}
        onToggleMonochrome={toggleMonochrome}
      />

      {/* Drawing and pipeline sidebar */}
      <div className="grid grid-cols-1 gap-3 xl:h-[calc(100dvh-200px)] xl:min-h-[620px] xl:grid-cols-[minmax(0,1fr)_540px]">

        <CadViewerCanvas
          containerRef={containerRef}
          viewerReady={viewerReady}
          viewerError={viewerError}
          onClear={clearSelection}
        />

        <CadViewerSidebar
          {...stageProps}
          activeStep={activeStep}
          pipelineContentRef={pipelineContentRef}
        />

      </div>
    </div>
  );
}