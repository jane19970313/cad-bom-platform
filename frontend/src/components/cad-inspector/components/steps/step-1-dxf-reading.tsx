"use client";

import type { StageProps } from "../../types/cad-viewer.types";
import { JsonInspector } from "../shared/json-inspector";

export function Step1DxfReading({
  analysis,
}: StageProps) {
  const metadata = {
    "File path": analysis.drawing.path,
    "DXF version": analysis.drawing.version,
    "Units code": analysis.drawing.units_code,
    "Units name": analysis.drawing.units_name,
    "Engine version": analysis.engine_version,
  };

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold">
        1. DXF Reading
      </h3>

      <div className="space-y-2">
        {Object.entries(metadata).map(([label, value]) => (
          <div key={label} className="cad-inspector-result-card rounded-md border p-3">
            <p className="text-xs text-muted-foreground">
              {label}
            </p>

            <p className="mt-1 break-all text-sm font-medium">
              {String(value ?? "—")}
            </p>
          </div>
        ))}
      </div>

      <h4 className="text-sm font-semibold">
        Reading warnings
      </h4>

      <JsonInspector data={analysis.drawing.warnings} />
    </div>
  );
}