"use client";

import type { RefObject } from "react";

import type {
  PipelineStep,
  StageProps,
} from "../types/cad-viewer.types";
import type { GeometryElement } from "../types/geometry-view.types";

import { Step1DxfReading } from "./steps/step-1-dxf-reading";
import { Step2EntityExtraction } from "./steps/step-2-entity-extraction";
import { Step3GeometryConversion } from "./steps/step-3-geometry-conversion";
import { Step4SpatialIndexing } from "./steps/step-4-spatial-indexing";
import { Step5ConnectivityGraph } from "./steps/step-5-connectivity-graph";
import { Step6EngineeringClassification } from "./steps/step-6-engineering-classification";
import { Step7RelationshipSerialization } from "./steps/step-7-relationship-serialization";
import { Step8PipelineSummary } from "./steps/step-8-pipeline-summary";

interface CadViewerSidebarProps extends StageProps {
  activeStep: PipelineStep;
  pipelineContentRef: RefObject<HTMLDivElement | null>;
}

export function CadViewerSidebar({
  activeStep,
  pipelineContentRef,
  ...stageProps
}: CadViewerSidebarProps) {
  return (
    <aside className="flex min-w-0 flex-col overflow-hidden rounded-xl border bg-background min-h-[420px] xl:min-h-0">
      <div
        ref={pipelineContentRef}
        className={`min-h-0 flex-1 p-3 ${
          activeStep === 5 || activeStep === 6
            ? "overflow-hidden"
            : "overflow-y-auto"
        }`}
      >
        {activeStep === 1 && (
          <Step1DxfReading {...stageProps} />
        )}

        {activeStep === 2 && (
          <Step2EntityExtraction {...stageProps} />
        )}

        {activeStep === 3 && (
          <Step3GeometryConversion {...stageProps} />
        )}

        {activeStep === 4 && (
          <Step4SpatialIndexing {...stageProps} />
        )}

        {activeStep === 5 && (
          <Step5ConnectivityGraph {...stageProps} />
        )}

        {activeStep === 6 && (
          <Step6EngineeringClassification {...stageProps} />
        )}

        {activeStep === 7 && (
          <Step7RelationshipSerialization {...stageProps} />
        )}

        {activeStep === 8 && (
          <Step8PipelineSummary {...stageProps} />
        )}
      </div>
    </aside>
  );
}