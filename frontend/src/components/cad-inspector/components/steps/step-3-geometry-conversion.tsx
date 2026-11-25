"use client";

import type { StageProps } from "../../types/cad-viewer.types";
import type { GeometryElement } from "../../types/geometry-view.types";

import { normalizeHandle } from "../../utils/handle-utils";
import { JsonInspector } from "../shared/json-inspector";
import { StatCard } from "../shared/stat-card";
import { GeometryView } from "../geometry-view";

export function Step3GeometryConversion({
  analysis,
  search,
  setSearch,
  selectedHandle,
  onSelectHandle,
}: StageProps) {
  const geometryElements: GeometryElement[] =
    analysis.geometry_elements ?? [];

  const diagnostics = analysis.diagnostics ?? [];

  const query = search.trim().toLowerCase();

  const filteredElements = query
    ? geometryElements.filter((element) => {
        const searchable = [
          element.source_handle,
          element.source_type,
          element.element_id,
          element.layer,
          element.geometry_type,
          element.caption,
          element.layout,
          ...(element.block_path ?? []),
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();

        return searchable.includes(query);
      })
    : geometryElements;

  return (
    <div className="flex h-full min-h-0 flex-col gap-2">
      <h3 className="text-sm font-semibold">
        3. Geometry Conversion
      </h3>

      {/* Statistics */}
      <div className="grid grid-cols-2 gap-2 shrink-0">
        <StatCard
          label="Converted geometries"
          value={geometryElements.length}
        />

        <StatCard
          label="Conversion diagnostics"
          value={diagnostics.length}
        />
      </div>

      {/* Search */}
      <input
        type="search"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        placeholder="Search handle, layer, type..."
        className="h-9 w-full shrink-0 rounded-md border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
      />

      {/* Geometry list */}
      <section className="flex min-h-[300px] flex-[1] flex-col overflow-hidden rounded-md border">
        <div className="shrink-0 border-b px-3 py-2">
          <h4 className="text-xs font-semibold">
            Converted geometries ({filteredElements.length})
          </h4>
        </div>

        <div className="min-h-0 flex-1 space-y-2 overflow-y-auto p-2">
          {filteredElements.map((element, index) => {
            const handle = element.source_handle;
            const normalized = normalizeHandle(handle);

            return (
              <details
                key={element.element_id ?? index}
                data-pipeline-handle={normalized}
                className={`rounded-md border p-3 ${
                  normalizeHandle(selectedHandle) === normalized
                    ? "border-primary bg-primary/10"
                    : ""
                }`}
              >
                <summary
                  onClick={() => onSelectHandle(handle)}
                  className="cursor-pointer text-sm font-medium"
                >
                  {element.geometry_type ?? "Unknown geometry"}
                  {" · "}
                  {handle ?? "No handle"}
                </summary>

                <div className="mt-3">
                  <JsonInspector data={element} />
                </div>
              </details>
            );
          })}

          {filteredElements.length === 0 && (
            <p className="p-4 text-sm text-muted-foreground">
              No matching elements.
            </p>
          )}

          {/* Diagnostics */}
          <div className="shrink-0 px-3 py-2">
            <h4 className="text-sm font-semibold">
              Conversion diagnostics
            </h4>

            <JsonInspector data={diagnostics} />
          </div>
        </div>
      </section>

      {/* Geometry Drawing View - Bottom */}
      {/* <section className="shrink-0 overflow-hidden rounded-md border">
        <div className="border-b px-3 py-2">
          <h4 className="text-xs font-semibold">
            Geometry Drawing View
          </h4>

          <p className="mt-1 text-xs text-muted-foreground">
            Hover to inspect and click to highlight the original CAD entity.
          </p>
        </div>

        <div className="p-2">
          <GeometryView
            elements={geometryElements}
            selectedHandle={selectedHandle}
            onSelectHandle={(handle) =>
              onSelectHandle(handle, null, true)
            }
          />
        </div>
      </section> */}
    </div>
  );
}