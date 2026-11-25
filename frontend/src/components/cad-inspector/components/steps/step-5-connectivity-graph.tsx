"use client";

import type { StageProps } from "../../types/cad-viewer.types";
import {
  getNodeHandle,
  normalizeHandle,
} from "../../utils/handle-utils";
import { JsonInspector } from "../shared/json-inspector";

export function Step5ConnectivityGraph({
  analysis,
  search,
  setSearch,
  selectedConnectivityNode,
  onSelectNode,
}: StageProps) {
  const nodes = analysis.connectivity_nodes ?? [];
  const relationships = analysis.relationships ?? [];

  const query = search.trim().toLowerCase();

  const filteredRelationships = query
    ? relationships.filter((relationship: any) => {
        const searchable = [
          relationship.source[1],
          relationship.target[1],
          relationship.relationship,
          relationship.association_method
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();

        return searchable.includes(query);
      })
    : relationships;

  return (
    <div className="flex h-full min-h-0 flex-col gap-2">
      <div className="shrink-0">
        <h3 className="text-sm font-semibold">
          5. Connectivity Graph
        </h3>

        <div className="mt-2 grid grid-cols-2 gap-2">
          <div className="cad-inspector-result-card rounded-md p-2">
            <p className="text-lg font-semibold">
              {analysis.summary.connectivity_node_count}
            </p>
            <p className="text-xs text-muted-foreground">
              Graph nodes
            </p>
          </div>

          <div className="rounded-md bg-muted p-2">
            <p className="text-lg font-semibold">
              {analysis.summary.connectivity_edge_count}
            </p>
            <p className="text-xs text-muted-foreground">
              Graph edges
            </p>
          </div>
        </div>
      </div>

      {/* Nodes and Edges - Two Column Layout */}
      <div className="grid min-h-0 flex-1 grid-cols-2 gap-2">
        {/* Nodes */}
        <section className="cad-inspector-result-panel flex min-h-0 flex-1 flex-col overflow-hidden rounded-md border">
          <div className="shrink-0 border-b px-3 py-2">
            <h4 className="text-sm font-semibold">
              Connectivity nodes
            </h4>
            <p className="text-[11px] text-muted-foreground">
              Select a node to highlight its connected edges.
            </p>
          </div>

          <div className="min-h-0 flex-1 space-y-2 overflow-y-auto p-2">
            {nodes.length === 0 ? (
              <JsonInspector
                data={nodes}
                emptyMessage="Graph nodes have not been serialized."
              />
            ) : (
              nodes.map((node: any, index: number) => {
                // const handle = getNodeHandle(node);
                const handle = node.split("'")[3];
                const normalized = normalizeHandle(handle);

                // const isSelected =
                //   normalizeHandle(selectedConnectivityNode) ===
                //   normalized;
                const isSelected =
                  normalizeHandle(selectedConnectivityNode?.split("'")[3] ?? "") ===
                  normalized;

                return (
                  <button
                    key={node?.id ?? normalized ?? index}
                    type="button"
                    data-pipeline-handle={normalized}
                    onClick={() => onSelectNode(handle)}
                    className={`cad-inspector-record w-full rounded-md border p-2 text-left transition hover:bg-muted/70 ${
                      isSelected
                        ? "border-primary bg-primary/10"
                        : ""
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-medium">
                        Graph node {index + 1}
                      </span>

                      <span className="font-mono text-xs text-muted-foreground">
                        {/* {handle || "No source handle"} */}
                        {node || "No source handle"}
                      </span>
                    </div>

                    {typeof node === "object" && node !== null && (
                      <pre className="mt-1 overflow-x-auto whitespace-pre-wrap break-words text-[10px] leading-relaxed text-muted-foreground">
                        {JSON.stringify(node, null, 2)}
                      </pre>
                    )}
                  </button>
                );
              })
            )}
          </div>
        </section>

        {/* Edges */}
        <section className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-md border">
          <div className="shrink-0 border-b px-3 py-2">
            <h4 className="text-sm font-semibold">
              Connectivity edges
            </h4>

            <p className="text-[11px] text-muted-foreground">
              {selectedConnectivityNode
                ? `Edges connected to ${selectedConnectivityNode} are highlighted.`
                : "Select a node above to highlight its connected edges."}
            </p>
          </div>

          <div className="p-2 pb-0">
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search handle, layer, type..."
              className="cad-inspector-search h-10 w-full rounded-md border px-3 text-sm outline-none focus:ring-2"
            />
          </div>

          <div className="min-h-0 flex-1 space-y-2 overflow-y-auto p-2">
            {filteredRelationships.length === 0 ? (
              <JsonInspector
                data={filteredRelationships}
                emptyMessage="No connectivity edges have been serialized."
              />
            ) : (
              filteredRelationships.map((relationship: any, index: number) => {
                // const selected = normalizeHandle(
                //   selectedConnectivityNode
                // );
                const selected = normalizeHandle(
                  selectedConnectivityNode?.split("'")[3] ?? ""
                );

                const source = normalizeHandle(
                  // getNodeHandle(relationship.source)
                  relationship.source[1]
                );

                const target = normalizeHandle(
                  // getNodeHandle(relationship.target)
                  relationship.target[1]
                );

                const isConnected =
                  Boolean(selected) &&
                  (source === selected || target === selected);

                return (
                  <div
                    key={relationship.id ?? index}
                    className={`cad-inspector-record rounded-md border p-2 transition ${
                      isConnected
                        ? "border-primary bg-primary/10"
                        : ""
                    }`}
                  >
                    <div className="flex flex-wrap items-center gap-2 text-xs">
                      <button
                        type="button"
                        onClick={() =>
                          // onSelectNode(
                          //   getNodeHandle(relationship.source)
                          // )
                          onSelectNode(relationship.source[1])
                        }
                        className="font-mono underline hover:text-primary"
                      >
                        {String(
                          getNodeHandle(relationship.source) ||
                            relationship.source
                        )}
                      </button>

                      <span>→</span>

                      <button
                        type="button"
                        onClick={() =>
                          // onSelectNode(
                          //   getNodeHandle(relationship.target)
                          // )
                          onSelectNode(relationship.target[1])
                        }
                        className="font-mono underline hover:text-primary"
                      >
                        {String(
                          getNodeHandle(relationship.target) ||
                            relationship.target
                        )}
                      </button>

                      {isConnected && (
                        <span className="ml-auto rounded bg-primary/15 px-2 py-0.5 text-[10px] font-medium text-primary">
                          Connected
                        </span>
                      )}
                    </div>

                    <details className="mt-1">
                      <summary className="cursor-pointer text-[10px] text-muted-foreground">
                        Relationship data
                      </summary>

                      <div className="mt-2">
                        <JsonInspector data={relationship} />
                      </div>
                    </details>
                  </div>
                );
              })
            )}
          </div>
        </section>
      </div>
    </div>
  );
}