"use client";

import { useCallback, useState } from "react";
import type { AnalysisElement } from "@/types/analysis";
import { normalizeHandle } from "../utils/handle-utils";

export function useCadSelection(elements: AnalysisElement[]) {
  const [selectedElement, setSelectedElement] =
    useState<AnalysisElement | null>(null);

  const [selectedHandle, setSelectedHandle] =
    useState<string | null>(null);

  const [selectedConnectivityNode, setSelectedConnectivityNode] =
    useState<string | null>(null);

  const [selectionMessage, setSelectionMessage] = useState("");

  const findElement = useCallback(
    (handle: unknown): AnalysisElement | null => {
      return (
        elements.find(
          (element) =>
            normalizeHandle(
              element.source_handle ?? element.handle
            ) === normalizeHandle(handle)
        ) ?? null
      );
    },
    [elements]
  );

  const reset = useCallback((message = "") => {
    setSelectedHandle(null);
    setSelectedElement(null);
    setSelectedConnectivityNode(null);
    setSelectionMessage(message);
  }, []);

  return {
    selectedElement,
    setSelectedElement,

    selectedHandle,
    setSelectedHandle,

    selectedConnectivityNode,
    setSelectedConnectivityNode,

    selectionMessage,
    setSelectionMessage,

    findElement,
    reset,
  };
}