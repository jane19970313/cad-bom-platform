"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock3,
  Database,
  FileCode2,
  Gauge,
  Loader2,
  Network,
  RefreshCw,
  Search,
  ShieldAlert,
  Workflow,
  XCircle,
} from "lucide-react";

import { ApiError, drawingsApi, processingApi, projectsApi } from "@/lib/api";
import type {
  PipelineStageProgress,
  ProcessingJobProgress,\n  ProcessingJob,
} from "@/types/processing";

import { useRouter } from "next/navigation";

type StageDefinition = {
  id: string;
  name: string;
  group: string;
  module: string;
  description: string;
};

const stages: StageDefinition[] = [
  {
    id: "dxf_reading",
    name: "DXF Reading",
    group: "Extraction",
    module: "extraction/reader.py",
    description: "Opens the original DXF document and reads drawing metadata.",
  },
  {
    id: "entity_extraction",
    name: "Entity Extraction",
    group: "Extraction",
    module: "extraction/entities.py",
    description: "Extracts modelspace entities while preserving handles, types, layers and source attributes.",
  },
  {
    id: "geometry_conversion",
    name: "Geometry Conversion",
    group: "Geometry",
    module: "geometry/converter.py",
    description: "Converts supported DXF entities into analysis-ready 2D geometry while retaining 3D coordinates.",
  },
  {
    id: "spatial_indexing",
    name: "Spatial Indexing",
    group: "Spatial Analysis",
    module: "spatial/index.py",
    description: "Builds a spatial index for efficient geometry queries.",
  },
  {
    id: "connectivity_graph",
    name: "Connectivity Graph",
    group: "Topology",
    module: "topology/graph_builder.py",
    description: "Builds a graph of geometric connectivity and candidate relationships.",
  },
  {
    id: "engineering_classification",
    name: "Engineering Classification",
    group: "Classification",
    module: "classification/engineering.py",
    description: "Classifies engineering elements using drawing context and conservative classification rules.",
  },
  {
    id: "relationship_serialization",
    name: "Relationship Serialization",
    group: "Output",
    module: "spatial/relationships.py",
    description: "Serializes relationships identified by the connectivity graph.",
  },
  {
    id: "summary_generation",
    name: "Summary Generation",
    group: "Output",
    module: "analysis/summary",
    description: "Generates the final analysis summary and aggregate counts.",
  },
];

const groups = [
  "Extraction",
  "Geometry",
  "Spatial Analysis",
  "Topology",
  "Classification",
  "Output",
];

function formatDuration(ms?: number | null): string {
  if (ms == null) return "—";

  if (ms < 1000) return `${ms} ms`;

  return `${(ms / 1000).toFixed(2)} s`;
}

function formatDate(value?: string | null): string {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return "—";

  return date.toLocaleString();
}

function statusStyle(status?: string) {
  switch (status?.toLowerCase()) {
    case "completed":
      return "border-green-200 bg-green-50 text-green-700";

    case "running":
    case "processing":
      return "border-blue-200 bg-blue-50 text-blue-700";

    case "failed":
      return "border-red-200 bg-red-50 text-red-700";

    case "queued":
    case "pending":
      return "border-amber-200 bg-amber-50 text-amber-700";

    default:
      return "border-slate-200 bg-slate-100 text-slate-500";
  }
}

function StageStatusIcon({ status }: { status?: string }) {
  switch (status?.toLowerCase()) {
    case "completed":
      return <CheckCircle2 size={19} className="text-green-600" />;

    case "running":
      return <Loader2 size={19} className="animate-spin text-blue-600" />;

    case "failed":
      return <XCircle size={19} className="text-red-600" />;

    default:
      return <Clock3 size={19} className="text-slate-400" />;
  }
}

function InfoField({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg bg-slate-50 p-3">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="mt-1 break-all text-sm font-semibold text-slate-700">
        {value}
      </p>
    </div>
  );
}

function MetricCard({
  label,
  value,
  detail,
  icon: Icon,
}: {
  label: string;
  value: string;
  detail: string;
  icon: React.ElementType;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">{label}</p>
        <Icon size={19} className="text-slate-400" />
      </div>

      <p className="mt-3 text-2xl font-bold">{value}</p>

      <p className="mt-1 text-xs text-slate-400">{detail}</p>
    </div>
  );
}

function StageDetails({
  stage,
  progress,
}: {
  stage: StageDefinition;
  progress?: PipelineStageProgress;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wider text-slate-400">
            Selected stage
          </p>

          <h2 className="mt-1 text-lg font-bold">{stage.name}</h2>
        </div>

        <span
          className={`rounded-full border px-2.5 py-1 text-xs font-medium ${statusStyle(
            progress?.status,
          )}`}
        >
          {progress?.status ?? "Not started"}
        </span>
      </div>

      <p className="mt-4 text-sm leading-6 text-slate-600">
        {stage.description}
      </p>

      <div className="mt-5 rounded-lg bg-slate-50 p-3">
        <p className="text-xs font-semibold text-slate-500">
          Backend module
        </p>

        <p className="mt-1 break-all font-mono text-xs text-slate-700">
          {stage.module}
        </p>
      </div>

      <div className="mt-5 space-y-3">
        <InfoField
          label="Started at"
          value={formatDate(progress?.started_at)}
        />

        <InfoField
          label="Completed at"
          value={formatDate(progress?.completed_at)}
        />

        <InfoField
          label="Duration"
          value={formatDuration(progress?.duration_ms)}
        />

        <InfoField
          label="Input count"
          value={progress?.input_count?.toLocaleString() ?? "Not reported"}
        />

        <InfoField
          label="Output count"
          value={progress?.output_count?.toLocaleString() ?? "Not reported"}
        />

        <InfoField
          label="Warning count"
          value={progress?.warning_count?.toLocaleString() ?? "Not reported"}
        />
      </div>

      {progress?.error && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3">
          <p className="text-sm font-semibold text-red-800">
            Stage error
          </p>

          <p className="mt-1 break-words text-sm text-red-700">
            {progress.error}
          </p>
        </div>
      )}
    </div>
  );
}

export default function PipelinePage() {
  const router = useRouter();

  const [jobInput, setJobInput] = useState("");\n  const [recentJobs, setRecentJobs] = useState<Array<{ job: ProcessingJob; filename: string; projectName: string }>>([]);\n  const [loadingJobs, setLoadingJobs] = useState(true);\n  const [manualEntry, setManualEntry] = useState(false);
  const [jobId, setJobId] = useState("");
  
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const urlJobId = params.get("jobId");

    if (urlJobId) {
      setJobInput(urlJobId);
      setJobId(urlJobId);
    }
  }, []);
  
  useEffect(() => {\n    let cancelled = false;\n    async function loadRecentJobs() {\n      setLoadingJobs(true);\n      try {\n        const projects = await projectsApi.getProjects();\n        const drawingGroups = await Promise.all(projects.map(async (project) => ({ projectName: project.name, drawings: (await drawingsApi.getProjectDrawings(project.id)).items })));\n        const groups = await Promise.all(drawingGroups.flatMap(group => group.drawings.map(async drawing => ({ projectName: group.projectName, filename: drawing.original_filename, jobs: (await processingApi.getDrawingJobs(drawing.id)).items }))));\n        if (cancelled) return;\n        const options = groups.flatMap(group => group.jobs.map(job => ({ job, filename: group.filename, projectName: group.projectName }))).sort((a,b) => new Date(b.job.created_at).getTime() - new Date(a.job.created_at).getTime());\n        setRecentJobs(options);\n        const requested = new URLSearchParams(window.location.search).get("jobId");\n        if (!requested && options.length && !jobId) { setJobInput(options[0].job.id); setJobId(options[0].job.id); }\n      } catch { if (!cancelled) setRecentJobs([]); }\n      finally { if (!cancelled) setLoadingJobs(false); }\n    }\n    void loadRecentJobs();\n    return () => { cancelled = true; };\n  }, []);\n\n  const [progress, setProgress] =
    useState<ProcessingJobProgress | null>(null);

  const [selectedStage, setSelectedStage] =
    useState("dxf_reading");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    if (!jobId) return;

    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function loadProgress() {
      try {
        setLoading(true);

        const result = await processingApi.getProcessingJobProgress(jobId);

        if (cancelled) return;

        setProgress(result);
        setError("");

        const status = result.status.toLowerCase();

        if (status === "queued" || status === "processing") {
          timer = setTimeout(loadProgress, 2000);
        }
      } catch (err) {
        if (cancelled) return;

        if (err instanceof ApiError) {
          setError(err.message);
        } else {
          setError("Unable to retrieve processing progress.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadProgress();

    return () => {
      cancelled = true;

      if (timer) {
        clearTimeout(timer);
      }
    };
  }, [jobId, refreshKey]);

  function handleInspect() {
    if (!jobId) return;

    router.push(
      `/pipeline/inspect?jobId=${encodeURIComponent(jobId)}`
    );
  }

  function handleSearch(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const value = jobInput.trim();

    if (!value) return;

    setError("");
    setProgress(null);
    setSelectedStage("dxf_reading");

    if (value === jobId) {
      setRefreshKey((current) => current + 1);
    } else {
      setJobId(value);
    }
  }

  const stageProgress = progress?.stage_progress?.stages ?? [];

  const completedCount = stageProgress.filter(
    (stage) => stage.status === "completed",
  ).length;

  const failedCount = stageProgress.filter(
    (stage) => stage.status === "failed",
  ).length;

  const warningCount = stageProgress.reduce(
    (total, stage) => total + (stage.warning_count ?? 0),
    0,
  );

  const totalDuration = stageProgress.reduce(
    (total, stage) => total + (stage.duration_ms ?? 0),
    0,
  );

  const selected =
    stages.find((stage) => stage.id === selectedStage) ?? stages[0];

  const selectedProgress = stageProgress.find(
    (stage) => stage.name === selected.id,
  );

  const jobStatus = progress?.status ?? "Not connected";

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white px-5 py-4 md:px-8">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white">
              <Workflow size={21} />
            </div>

            <div>
              <p className="text-sm font-bold">DXF2BOM</p>
              <p className="text-xs text-slate-500">
                Live Pipeline Monitor
              </p>
            </div>
          </div>

          <a
            href="/"
            className="text-sm font-medium text-blue-600 hover:text-blue-700"
          >
            Back to dashboard
          </a>
        </div>
      </header>

      <div className="mx-auto max-w-7xl space-y-6 p-5 md:p-8">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <p className="mb-2 text-xs text-slate-400">
              Engineering / Pipeline Monitor
            </p>

            <h1 className="text-2xl font-bold tracking-tight">
              Pipeline Monitor
            </h1>

            <p className="mt-1 text-sm text-slate-500">
              Monitor actual DXF processing execution and stage progress.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span
              className={`rounded-full border px-3 py-1.5 text-xs font-medium ${statusStyle(
                progress?.status,
              )}`}
            >
              {jobStatus}
            </span>

            <button
              type="button"
              disabled={!jobId || loading}
              onClick={() => setRefreshKey((value) => value + 1)}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium hover:bg-slate-50 disabled:opacity-50"
            >
              <RefreshCw size={15} />
              Refresh
            </button>
          </div>
        </div>

        {/* Job selector */}
        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="mb-4 flex items-center gap-2">
            <FileCode2 size={19} className="text-blue-600" />

            <h2 className="font-semibold">Processing job</h2>
          </div>

          <form
            onSubmit={handleSearch}
            className="flex flex-col gap-3 sm:flex-row"
          >
            <input
              value={jobInput}
              onChange={(event) => setJobInput(event.target.value)}
              placeholder="Enter processing job UUID"
              className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />

            <button
              type="submit"
              disabled={!jobInput.trim()}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
            >
              <Search size={16} />
              Monitor job
            </button>
          </form>

          {error && (
            <div
              role="alert"
              className="mt-4 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700"
            >
              <AlertTriangle size={17} className="mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {progress && (
            <div className="mt-5 grid gap-3 md:grid-cols-3">
              <InfoField label="Processing job ID" value={progress.job_id} />

              <InfoField label="Drawing ID" value={progress.drawing_id} />

              <InfoField
                label="Attempt count"
                value={String(progress.attempt_count)}
              />

              <InfoField
                label="Created at"
                value={formatDate(progress.created_at)}
              />

              <InfoField
                label="Started at"
                value={formatDate(progress.started_at)}
              />

              <InfoField
                label="Completed at"
                value={formatDate(progress.completed_at)}
              />
            </div>
          )}

          {progress?.error_message && (
            <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {progress.error_message}
            </div>
          )}

          {jobId && (
            <p className="mt-4 flex items-center gap-2 text-xs text-slate-400">
              {loading ? (
                <>
                  <Loader2 size={13} className="animate-spin" />
                  Updating processing progress...
                </>
              ) : progress?.status === "processing" ||
                progress?.status === "queued" ? (
                <>
                  <Activity size={13} className="text-blue-500" />
                  Automatic updates every 2 seconds.
                </>
              ) : progress ? (
                <>
                  <CheckCircle2 size={13} />
                  Automatic polling stopped.
                </>
              ) : (
                "Waiting for job information."
              )}
            </p>
          )}

          {progress && progress.status === "completed" && (
            <div className="mt-5 flex justify-end">
              <button
                type="button"
                onClick={handleInspect}
                className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700"
              >
                <Search size={16} />
                Inspect Drawing
                <ArrowRight size={16} />
              </button>
            </div>
          )}
        </section>

        {/* Summary metrics */}
        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            icon={Workflow}
            label="Pipeline stages"
            value="8"
            detail="Actual backend stages"
          />

          <MetricCard
            icon={CheckCircle2}
            label="Completed stages"
            value={String(completedCount)}
            detail={`Out of ${stages.length}`}
          />

          <MetricCard
            icon={Clock3}
            label="Total reported stage time"
            value={formatDuration(totalDuration)}
            detail="Sum of reported durations"
          />

          <MetricCard
            icon={ShieldAlert}
            label="Warnings"
            value={String(warningCount)}
            detail={`${failedCount} failed stages`}
          />
        </section>

        {/* Pipeline stages and details */}
        <section className="grid gap-6 xl:grid-cols-5">
          <div className="rounded-xl border border-slate-200 bg-white p-5 xl:col-span-3">
            <div className="mb-5 flex items-center justify-between">
              <div>
                <h2 className="font-semibold">Processing workflow</h2>

                <p className="mt-1 text-xs text-slate-500">
                  Select a stage to inspect actual execution details.
                </p>
              </div>

              <Activity size={20} className="text-slate-400" />
            </div>

            <div className="space-y-4">
              {groups.map((group) => {
                const groupStages = stages.filter(
                  (stage) => stage.group === group,
                );

                return (
                  <div key={group}>
                    <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
                      {group}
                    </p>

                    <div className="space-y-2">
                      {groupStages.map((stage) => {
                        const stageData = stageProgress.find(
                          (item) => item.name === stage.id,
                        );

                        const active = selectedStage === stage.id;

                        return (
                          <button
                            key={stage.id}
                            type="button"
                            onClick={() => setSelectedStage(stage.id)}
                            className={`flex w-full items-center gap-3 rounded-lg border p-3 text-left transition ${
                              active
                                ? "border-blue-300 bg-blue-50"
                                : "border-slate-200 hover:bg-slate-50"
                            }`}
                          >
                            <StageStatusIcon status={stageData?.status} />

                            <div className="min-w-0 flex-1">
                              <p className="text-sm font-semibold">
                                {stage.name}
                              </p>

                              <p className="mt-0.5 truncate text-xs text-slate-500">
                                {stage.module}
                              </p>
                            </div>

                            <span
                              className={`shrink-0 rounded-full border px-2 py-1 text-[11px] font-medium ${statusStyle(
                                stageData?.status,
                              )}`}
                            >
                              {stageData?.status ?? "Pending"}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="space-y-5 xl:col-span-2">
            <StageDetails
              stage={selected}
              progress={selectedProgress}
            />

            <div className="rounded-xl border border-slate-200 bg-white p-5">
              <div className="mb-4 flex items-center gap-2">
                <Gauge size={18} className="text-blue-600" />
                <h3 className="font-semibold">Live stage metrics</h3>
              </div>

              <div className="space-y-3">
                <InfoField
                  label="Current stage"
                  value={
                    stages.find(
                      (stage) =>
                        stage.id === progress?.stage_progress?.current_stage,
                    )?.name ??
                    progress?.stage_progress?.current_stage ??
                    "Not reported"
                  }
                />

                <InfoField
                  label="Overall pipeline status"
                  value={
                    progress?.stage_progress?.overall_status ??
                    "Not reported"
                  }
                />

                <InfoField
                  label="Last progress update"
                  value={formatDate(progress?.stage_progress?.updated_at)}
                />

                <InfoField
                  label="Reported stage events"
                  value={`${stageProgress.length} / 8`}
                />
              </div>
            </div>
          </div>
        </section>

        {/* Diagnostics */}
        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="mb-4 flex items-center gap-2">
            <Database size={19} className="text-blue-600" />
            <h2 className="font-semibold">Diagnostics & validation</h2>
          </div>

          {stageProgress.filter(
            (stage) => stage.error || stage.status === "failed",
          ).length > 0 ? (
            <div className="space-y-3">
              {stageProgress
                .filter(
                  (stage) => stage.error || stage.status === "failed",
                )
                .map((stage) => (
                  <div
                    key={stage.name}
                    className="rounded-lg border border-red-200 bg-red-50 p-3"
                  >
                    <p className="text-sm font-semibold text-red-800">
                      {stage.name}
                    </p>

                    <p className="mt-1 break-words text-sm text-red-700">
                      {stage.error ?? "Stage failed without an error message."}
                    </p>
                  </div>
                ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">
              {progress
                ? "No stage failures have been reported."
                : "Enter a processing job ID to load live diagnostics."}
            </p>
          )}

          {progress?.stage_progress?.error && (
            <p className="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">
              {progress.stage_progress.error}
            </p>
          )}
        </section>

        <footer className="border-t border-slate-200 pt-5 text-xs text-slate-400">
          DXF2BOM · Live pipeline monitor · Connected to FastAPI
        </footer>
      </div>
    </main>
  );
}