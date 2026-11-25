"use client";

import type { StageProps } from "../../types/cad-viewer.types";
import { normalizeHandle } from "../../utils/handle-utils";
import { JsonInspector } from "../shared/json-inspector";

export function Step6EngineeringClassification({
  analysis,
  selectedHandle,
  selectedElement,
  selectionMessage,
  viewerReady,
  handleStats,
  search,
  setSearch,
  onSelectHandle,
}: StageProps) {
  const elements = analysis.elements ?? [];

  const query = search.trim().toLowerCase();

  const filteredElements = query
    ? elements.filter((element: any) => {
        const searchable = [
          element.source_handle,
          element.handle,
          element.id,
          element.engineering_type,
          element.classification,
          element.entity_type,
          element.dxf_type,
          element.layer,
          element.geometry_type,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();

        return searchable.includes(query);
      })
    : elements;

  return (
    <div className="flex h-full min-h-0 flex-col gap-2">
      <div className="shrink-0 space-y-2">
        <h3 className="text-sm font-semibold">
          6. Engineering Classification
        </h3>

        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="rounded-md bg-muted p-2">
            <p className="text-lg font-semibold">
              {handleStats.total}
            </p>
            <p className="text-[11px] text-muted-foreground">
              Total
            </p>
          </div>

          <div className="rounded-md bg-muted p-2">
            <p className="text-lg font-semibold">
              {handleStats.resolved}
            </p>
            <p className="text-[11px] text-muted-foreground">
              Resolved
            </p>
          </div>

          <div className="rounded-md bg-muted p-2">
            <p className="text-lg font-semibold">
              {handleStats.missing}
            </p>
            <p className="text-[11px] text-muted-foreground">
              Missing
            </p>
          </div>
        </div>

        <input
          type="search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search handle, layer, type..."
          className="h-9 w-full rounded-md border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
        />
      </div>

      {/* Classified elements */}
      <section className="flex min-h-0 flex-[0.8] flex-col overflow-hidden rounded-md border">
        <div className="shrink-0 border-b px-3 py-2">
          <h4 className="text-xs font-semibold">
            Classified elements ({filteredElements.length})
          </h4>
        </div>

        <div className="min-h-0 flex-1 divide-y overflow-y-auto">
          {filteredElements.map((element, index) => {
            const handle = String(
              element.source_handle ?? element.handle ?? ""
            );

            const normalized = normalizeHandle(handle);

            return (
              <button
                key={handle || element.id || index}
                data-pipeline-handle={normalized}
                type="button"
                disabled={!viewerReady}
                onClick={() => onSelectHandle(handle, element)}
                className={`w-full px-3 py-2 text-left transition hover:bg-muted/70 ${
                  selectedHandle === normalized
                    ? "border-l-2 border-primary bg-primary/10"
                    : ""
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-xs font-medium">
                    {element.engineering_type ||
                      element.classification ||
                      element.entity_type ||
                      "Unclassified"}
                  </span>

                  <span className="shrink-0 rounded bg-muted px-2 py-0.5 font-mono text-[10px]">
                    {handle || "No handle"}
                  </span>
                </div>

                <div className="mt-1 flex flex-wrap gap-3 text-[10px] text-muted-foreground">
                  <span>
                    DXF: {element.dxf_type || element.entity_type || "—"}
                  </span>

                  <span>
                    Layer: {element.layer || "—"}
                  </span>
                </div>
              </button>
            );
          })}

          {filteredElements.length === 0 && (
            <p className="p-4 text-sm text-muted-foreground">
              No matching elements.
            </p>
          )}
        </div>
      </section>

      {/* Selected element properties */}
      <section className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-md border">
        <div className="shrink-0 border-b px-3 py-2">
          <h4 className="text-xs font-semibold">
            Selected element properties
          </h4>

          {selectedElement && (
            <p className="mt-1 truncate font-mono text-[10px] text-muted-foreground">
              Handle:{" "}
              {String(
                selectedElement.source_handle ??
                  selectedElement.handle ??
                  "—"
              )}
            </p>
          )}
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-2">
          {selectedElement ? (
            <JsonInspector data={selectedElement} />
          ) : (
            <div className="flex h-full items-center justify-center text-center text-xs text-muted-foreground">
              Select an element from the list or directly in the drawing.
            </div>
          )}
        </div>

        {selectionMessage && (
          <div className="shrink-0 border-t px-3 py-2 text-[10px] text-muted-foreground">
            {selectionMessage}
          </div>
        )}
      </section>
    </div>
  );
}