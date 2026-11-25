"use client";

import type { StageProps } from "../../types/cad-viewer.types";
import { JsonInspector } from "../shared/json-inspector";

export function Step7RelationshipSerialization({
  analysis,
  onSelectHandle,
}: StageProps) {
  const relationships = analysis.relationships ?? [];

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold">
        7. Relationship Serialization
      </h3>

      <p className="text-xs text-muted-foreground">
        {relationships.length.toLocaleString()} serialized relationships.
      </p>

      {relationships.map((relationship: any, index: number) => (
        <details
          key={relationship.id ?? index}
          className="cad-inspector-record rounded-md border p-3"
        >
          <summary className="cursor-pointer text-sm font-medium">
            {String(relationship.source)}
            {" → "}
            {String(relationship.target)}
          </summary>

          <div className="mt-3 flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => onSelectHandle(relationship.source)}
              className="cad-inspector-action rounded-md border px-3 py-2 text-xs hover:bg-muted"
            >
              Select source
            </button>

            <button
              type="button"
              onClick={() => onSelectHandle(relationship.target)}
              className="rounded-md border px-3 py-2 text-xs hover:bg-muted"
            >
              Select target
            </button>
          </div>

          <div className="mt-3">
            <JsonInspector data={relationship} />
          </div>
        </details>
      ))}
    </div>
  );
}