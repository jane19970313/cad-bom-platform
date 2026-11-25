"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import {
  drawingsApi,
  processingApi,
  analysisApi,
} from "@/lib/api";

import type {
  DxfAnalysisResult,
} from "@/types/analysis";

import { CadViewer } from "@/components/cad-inspector/cad-viewer";

interface InspectorClientProps {
  jobId: string;
}

export default function InspectorClient({ jobId }: InspectorClientProps) {
  const [result, setResult] = useState<DxfAnalysisResult | null>(null);
  const [dxfData, setDxfData] = useState<ArrayBuffer | null>(null);

  const [loading, setLoading] = useState(true);
  const [dxfLoading, setDxfLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dxfError, setDxfError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadInspectorData() {
      if (!jobId) {
        setError("No processing job ID was provided in the URL.");
        setLoading(false);
        return;
      }

      const startedAt = performance.now();

      try {
        setLoading(true);
        setDxfLoading(false);
        setError(null);
        setDxfError(null);
        setResult(null);
        setDxfData(null);

        console.log("[Inspector] Loading job and analysis in parallel...");

        const [progress, analysisResult] = await Promise.all([
          processingApi.getProcessingJobProgress(jobId),
          analysisApi.getAnalysisResult(jobId),
        ]);

        if (cancelled) return;

        console.log(
          `[Inspector] Job and analysis loaded in ${(
            performance.now() - startedAt
          ).toFixed(0)} ms`
        );

        if (progress.status !== "completed") {
          throw new Error(
            `This job is not completed. Current status: ${progress.status}`
          );
        }

        // Validate the complete analysis response.
        if (!analysisResult || !Array.isArray(analysisResult.elements)) {
          throw new Error(
            "The analysis response is invalid or does not contain elements."
          );
        }

        // Display analysis immediately.
        setResult(analysisResult);
        setLoading(false);

        // Download original DXF independently.
        setDxfLoading(true);

        const dxfStartedAt = performance.now();

        console.log("[Inspector] Downloading original DXF...");

        try {
          const drawingData = await drawingsApi.downloadDrawingDxf(
            progress.drawing_id
          );

          if (cancelled) return;

          console.log(
            `[Inspector] DXF downloaded: ${drawingData.byteLength} bytes in ${(
              performance.now() - dxfStartedAt
            ).toFixed(0)} ms`
          );

          setDxfData(drawingData);
        } catch (downloadError) {
          if (!cancelled) {
            const message =
              downloadError instanceof Error
                ? downloadError.message
                : "Could not download the original DXF.";

            setDxfError(message);

            console.error(
              "[Inspector] DXF download failed:",
              downloadError
            );
          }
        } finally {
          if (!cancelled) {
            setDxfLoading(false);
          }
        }
      } catch (err) {
        if (!cancelled) {
          const message =
            err instanceof Error
              ? err.message
              : "Could not load the engineering inspection data.";

          setError(message);
          setLoading(false);

          console.error("[Inspector] Loading failed:", err);
        }
      }
    }

    void loadInspectorData();

    return () => {
      cancelled = true;
    };
  }, [jobId]);

  if (loading) {
    return (
      <main className="mx-auto max-w-[1600px] p-6">
        <p className="text-sm text-muted-foreground">
          Loading job and analysis data…
        </p>
      </main>
    );
  }

  if (error) {
    return (
      <main className="mx-auto max-w-[1600px] space-y-4 p-6">
        <Link
          href="/pipeline"
          className="text-sm text-primary hover:underline"
        >
          ← Back to pipeline
        </Link>

        <div className="rounded-xl border p-6">
          <h1 className="font-semibold">
            Unable to open inspector
          </h1>

          <p className="mt-2 text-sm text-destructive">
            {error}
          </p>
        </div>
      </main>
    );
  }

  if (!result) return null;

  const summary = result.summary ?? {};

  return (
    <main className="w-full space-y-5 p-3 md:p-5">

      {/* Page header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link
            href="/pipeline"
            className="text-sm text-primary hover:underline"
          >
            ← Back to pipeline
          </Link>

          <h1 className="mt-3 text-2xl font-semibold tracking-tight">
            DXF Engineering Inspector
          </h1>

          <p className="mt-1 text-sm text-muted-foreground">
            Inspect all eight DXF processing stages alongside the original
            engineering drawing.
          </p>
        </div>

        <div className="rounded-lg border px-3 py-2">
          <p className="text-xs text-muted-foreground">
            Processing job
          </p>

          <p className="font-mono text-xs">
            {jobId}
          </p>
        </div>
      </div>

      {/* Analysis summary */}
      <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Metric
          label="Raw entities"
          value={summary.raw_entity_count}
        />

        <Metric
          label="Geometry elements"
          value={summary.geometry_element_count}
        />

        <Metric
          label="Classified elements"
          value={summary.classified_element_count}
        />

        <Metric
          label="Classes"
          value={summary.bom_element_count}
        />

        {/* <Metric
          label="Conversion failures"
          value={summary.geometry_conversion_failure_count}
        /> */}
        
      </section>

      {/* CAD viewer + eight-stage inspector */}
      {dxfData ? (
        <CadViewer
          dxfData={dxfData}
          analysis={result}
        />
      ) : (
        <section className="flex min-h-[650px] items-center justify-center rounded-xl border bg-background p-6">
          <div className="max-w-md text-center">

            {dxfLoading ? (
              <>
                <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-4 border-muted border-t-primary" />

                <h2 className="font-semibold">
                  Loading original DXF drawing
                </h2>

                <p className="mt-2 text-sm text-muted-foreground">
                  Your eight-stage analysis results are ready.
                  The original drawing is downloading now.
                </p>
              </>
            ) : (
              <>
                <h2 className="font-semibold text-destructive">
                  Drawing unavailable
                </h2>

                <p className="mt-2 text-sm text-muted-foreground">
                  {dxfError || "The DXF drawing has not loaded."}
                </p>
              </>
            )}

          </div>
        </section>
      )}

    </main>
  );
}

function Metric({
  label,
  value,
}: {
  label: string;
  value: unknown;
}) {
  return (
    <div className="rounded-xl border bg-background p-4">
      <p className="text-xs text-muted-foreground">
        {label}
      </p>

      <p className="mt-1 text-2xl font-semibold tabular-nums">
        {typeof value === "number"
          ? value.toLocaleString()
          : "—"}
      </p>
    </div>
  );
}