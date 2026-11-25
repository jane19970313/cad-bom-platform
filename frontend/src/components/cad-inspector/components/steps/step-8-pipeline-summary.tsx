"use client";

import type { StageProps } from "../../types/cad-viewer.types";
import { JsonInspector } from "../shared/json-inspector";
import * as XLSX from "xlsx";
import { Download } from "lucide-react";

export function Step8PipelineSummary({
  analysis,
}: StageProps) {
  const bomElements = analysis.bom_elements ?? [];

  const handleExportExcel = () => {
    if (bomElements.length === 0) return;

    const worksheet = XLSX.utils.json_to_sheet(
      bomElements.map((element) => ({
        ...element,
      }))
    );

    const workbook = XLSX.utils.book_new();

    XLSX.utils.book_append_sheet(
      workbook,
      worksheet,
      "Bill of Materials"
    );

    XLSX.writeFile(workbook, "bill-of-materials.xlsx");
  };

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold">
        8. Pipeline Summary
      </h3>

      {/* Existing summary */}
      <div className="grid grid-cols-2 gap-2">
        {Object.entries(analysis.summary).map(([key, value]) => (
          <div key={key} className="rounded-md bg-muted p-3">
            <p className="text-xl font-semibold">
              {Number(value).toLocaleString()}
            </p>

            <p className="mt-1 break-words text-xs text-muted-foreground">
              {key.replaceAll("_", " ")}
            </p>
          </div>
        ))}
      </div>

      {/* Existing diagnostics */}
      <h4 className="text-sm font-semibold">
        Complete diagnostics
      </h4>

      <JsonInspector data={analysis.diagnostics ?? []} />

      {/* Existing settings */}
      <h4 className="text-sm font-semibold">
        Pipeline settings
      </h4>

      <JsonInspector data={analysis.settings} />

      {/* New BOM Elements section */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold">
            Bill of Materials
          </h4>

          <button
            type="button"
            onClick={handleExportExcel}
            disabled={bomElements.length === 0}
            className="cad-inspector-action inline-flex items-center gap-2 rounded-md border px-3 py-2 text-xs font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Download className="h-4 w-4" />
            Export Excel
          </button>
        </div>

        <p className="text-xs text-muted-foreground">
          {bomElements.length.toLocaleString()} BOM elements generated.
        </p>

        <section className="overflow-hidden rounded-md border">
          <div className="border-b px-3 py-2">
            <h5 className="text-xs font-semibold">
              BOM Elements ({bomElements.length})
            </h5>
          </div>

          <div className="max-h-[400px] space-y-2 overflow-y-auto p-2">
            {bomElements.map((element, index) => (
              <details
                key={`${element.caption}-${index}`}
                className="cad-inspector-record rounded-md border p-3"
              >
                <summary className="cursor-pointer text-sm font-medium">
                  <span>{element.caption}</span>
                  <span className="ml-2 text-muted-foreground">
                    · {element.count.toLocaleString()} items
                  </span>
                </summary>

                <div className="mt-3">
                  <JsonInspector data={element} />
                </div>
              </details>
            ))}

            {bomElements.length === 0 && (
              <p className="p-4 text-sm text-muted-foreground">
                No BOM elements generated.
              </p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}