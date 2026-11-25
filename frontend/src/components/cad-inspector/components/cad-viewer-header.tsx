"use client";

import {
  PIPELINE_STEPS,
  type PipelineStep,
} from "../types/cad-viewer.types";

interface CadViewerHeaderProps {
  activeStep: PipelineStep;
  setActiveStep: (step: PipelineStep) => void;
  viewerReady: boolean;
  monochrome: boolean;
  onClear: () => void;
  onToggleMonochrome: () => void;
}

export function CadViewerHeader({
  activeStep,
  setActiveStep,
  viewerReady,
  monochrome,
  onClear,
  onToggleMonochrome,
}: CadViewerHeaderProps) {
  return (
    <>
      <div className="flex items-center justify-between border-b px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold">
            DXF Pipeline Inspector
          </h2>

          <p className="mt-1 text-xs text-muted-foreground">
            Inspect all 8 processing stages
          </p>
        </div>

        <span className="rounded-md bg-muted px-2 py-1 text-xs">
          Step {activeStep}/8
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-3 py-3">
        <div className="grid min-w-0 flex-1 grid-cols-4 gap-2 sm:grid-cols-8">
          {PIPELINE_STEPS.map((step) => (
            <button
              key={step.id}
              type="button"
              onClick={() =>
                setActiveStep(step.id as PipelineStep)
              }
              className={`rounded-md border px-2 py-2 text-xs font-medium transition-colors ${
                activeStep === step.id
                  ? "border-primary bg-primary text-primary-foreground"
                  : "bg-background hover:bg-muted"
              }`}
            >
              <span className="block text-[10px] opacity-70">
                STEP {step.id}
              </span>

              <span className="block truncate">
                {step.short}
              </span>
            </button>
          ))}
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            onClick={onClear}
            disabled={!viewerReady}
            className="whitespace-nowrap rounded-md border px-3 py-2 text-xs hover:bg-muted disabled:opacity-50"
          >
            Clear selection
          </button>

          <button
            type="button"
            onClick={onToggleMonochrome}
            disabled={!viewerReady}
            className="whitespace-nowrap rounded-md border px-3 py-2 text-xs hover:bg-muted disabled:opacity-50"
          >
            {monochrome ? "Restore Colors" : "Monochrome"}
          </button>
        </div>
      </div>
    </>
  );
}