"use client";

import type { StageProps } from "../../types/cad-viewer.types";
import { normalizeHandle } from "../../utils/handle-utils";
import { JsonInspector } from "../shared/json-inspector";

export function Step4SpatialIndexing({
  analysis,
  selectedHandle,
  onSelectHandle,
}: StageProps) {
  const geometryElements = analysis.geometry_elements ?? [];

  const indexedCount =
    analysis.spatial_index?.indexed_element_count ??
    geometryElements.length;

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold">
        4. Spatial Indexing
      </h3>

      <div className="cad-inspector-result-card rounded-md p-3">
        <p className="text-2xl font-semibold">
          {indexedCount}
        </p>

        <p className="text-xs text-muted-foreground">
          Elements supplied to the spatial index
        </p>
      </div>

      <h4 className="text-sm font-semibold">
        Spatial indexing settings
      </h4>

      <JsonInspector
        data={{
          flattening_distance:
            analysis.settings.flattening_distance,
          nearby_distance:
            analysis.settings.nearby_distance,
          connectivity_tolerance:
            analysis.settings.connectivity_tolerance,
          indexed_element_count: indexedCount,
        }}
      />

      <h4 className="text-sm font-semibold">
        Indexed geometry elements
      </h4>

      {geometryElements.map((element: any, index: number) => {
        const handle = element.source_handle;
        const normalized = normalizeHandle(handle);

        return (
          <button
            key={element.element_id ?? index}
            type="button"
            data-pipeline-handle={normalized}
            onClick={() => onSelectHandle(handle)}
            className={`cad-inspector-result-card w-full rounded-md border p-3 text-left hover:bg-muted/70 ${
              selectedHandle === normalized
                ? "border-primary bg-primary/10"
                : ""
            }`}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-medium">
                {element.geometry_type ?? "Unknown geometry"}
              </span>

              <span className="font-mono text-xs">
                {handle || "No handle"}
              </span>
            </div>
          </button>
        );
      })}

      <p className="text-xs text-muted-foreground">
        This shows indexing inputs and configuration.
        The internal SpatialIndex structure is not currently
        serialized by the backend.
      </p>
    </div>
  );
}