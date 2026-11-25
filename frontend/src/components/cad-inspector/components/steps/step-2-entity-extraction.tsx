"use client";

import type { StageProps } from "../../types/cad-viewer.types";
import { normalizeHandle } from "../../utils/handle-utils";
import { JsonInspector } from "../shared/json-inspector";

export function Step2EntityExtraction({
  analysis,
  search,
  setSearch,
  selectedHandle,
  onSelectHandle,
}: StageProps) {
  const rawEntities = analysis.raw_entities ?? [];

  const query = search.trim().toLowerCase();

  const filteredEntities = query
    ? rawEntities.filter((entity: any) => {
        const searchable = [
          entity.source.entity_handle,
          entity.source.entity_type,
          entity.source.layer,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();

        return searchable.includes(query);
      })
    : rawEntities;

  return (
    <div className="flex h-full min-h-0 flex-col gap-2">
      <h3 className="text-sm font-semibold">
        2. Entity Extraction
      </h3>

      <p className="text-xs text-muted-foreground">
        {rawEntities.length.toLocaleString()} raw entities extracted.
      </p>

      <input
        type="search"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        placeholder="Search handle, layer, type..."
        className="cad-inspector-search h-10 w-full rounded-md border px-3 text-sm outline-none focus:ring-2"
      />

      <section className="cad-inspector-result-panel flex min-h-0 flex-[1] flex-col overflow-hidden rounded-md border">
        <div className="shrink-0 border-b px-3 py-2">
          <h4 className="text-xs font-semibold">
            Extracted entities ({filteredEntities.length})
          </h4>
        </div>

        <div className="space-y-2 p-2 min-h-0 flex-1 divide-y overflow-y-auto">

          {filteredEntities.map((entity: any, index: number) => {
            const handle = entity.source?.entity_handle;
            const normalized = normalizeHandle(handle);

            return (
              <details
                key={handle ?? index}
                data-pipeline-handle={normalized}
                className={`cad-inspector-record rounded-md border p-3 ${
                  selectedHandle === normalized
                    ? "border-primary bg-primary/10"
                    : ""
                }`}
              >
                <summary
                  onClick={() => onSelectHandle(handle)}
                  className="cursor-pointer text-sm font-medium"
                >
                  {entity.source?.entity_type ?? "Unknown entity"}
                  {" · "}
                  {handle ?? "No handle"}
                </summary>

                <div className="mt-3">
                  <JsonInspector data={entity} />
                </div>
              </details>
            );
          })}

          {filteredEntities.length === 0 && (
            <p className="p-4 text-sm text-muted-foreground">
              No matching entities.
            </p>
          )}
        </div>
      </section>
    </div>
  );
}