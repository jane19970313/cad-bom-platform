"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Box,
  FileCode2,
  FolderKanban,
  Workflow,
  AlertCircle,
  CheckCircle2,
  Circle,
  Clock3,
  LoaderCircle,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import {
  projectsApi,
  drawingsApi,
  processingApi,
} from "@/lib/api";

import type { Project } from "@/types/project";
import type { Drawing } from "@/types/drawing";
import type {
  ProcessingJob,
  StageProgress,
  PipelineStageProgress,
} from "@/types/processing";

type DashboardDrawing = Drawing & {
  project_name: string;
};

type DashboardJob = ProcessingJob & {
  drawing_name: string;
  project_name: string;
};

type DashboardDataState = {
  projects: Project[];
  allDrawings: DashboardDrawing[];
  drawings: DashboardDrawing[];
  drawingTotal: number;
  jobs: DashboardJob[];
  jobTotal: number;
  warnings: string[];
};

function formatDate(value: string | null): string {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return "—";

  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

function normalizeStatus(status: string): string {
  return status.toLowerCase().replace(/[\s-]+/g, "_");
}

function formatStatus(status: string): string {
  return status
    .replace(/[_-]/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function isActiveJob(status: string): boolean {
  return ["queued", "pending", "processing", "running", "in_progress"]
    .includes(normalizeStatus(status));
}

function formatStageName(name: string): string {
  const labels: Record<string, string> = {
    dxf_reading: "DXF reading",
    entity_extraction: "Entity extraction",
    geometry_conversion: "Geometry conversion",
    spatial_indexing: "Spatial indexing",
    connectivity_graph: "Connectivity graph",
    engineering_classification: "Engineering classification",
    relationship_serialization: "Relationship serialization",
    summary_generation: "Summary generation",
  };

  return labels[name] ?? formatStatus(name);
}

function formatDuration(value: number | null | undefined): string {
  if (value == null) return "—";
  if (value < 1000) return `${value} ms`;

  return `${(value / 1000).toFixed(2)} s`;
}

function StageStatusIcon({ status }: { status: string }) {
  const normalized = normalizeStatus(status);

  if (normalized === "completed" || normalized === "success") {
    return <CheckCircle2 className="text-emerald-600" size={20} />;
  }

  if (normalized === "running" || normalized === "processing") {
    return <LoaderCircle className="animate-spin text-blue-600" size={20} />;
  }

  if (normalized === "failed" || normalized === "error") {
    return <AlertCircle className="text-red-600" size={20} />;
  }

  return <Circle className="text-slate-300" size={20} />;
}

function StageProgressRow({
  stage,
}: {
  stage: PipelineStageProgress;
}) {
  return (
    <div className="flex gap-3 border-b border-slate-100 py-4 last:border-0">
      <div className="pt-0.5">
        <StageStatusIcon status={stage.status} />
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm font-medium text-slate-800">
            {formatStageName(stage.name)}
          </p>
          <StatusBadge status={stage.status} />
        </div>

        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
          <span>Duration: {formatDuration(stage.duration_ms)}</span>

          {stage.input_count != null && (
            <span>Input: {stage.input_count.toLocaleString()}</span>
          )}

          {stage.output_count != null && (
            <span>Output: {stage.output_count.toLocaleString()}</span>
          )}

          {stage.warning_count != null && (
            <span>Warnings: {stage.warning_count.toLocaleString()}</span>
          )}
        </div>

        {stage.error && (
          <p className="mt-2 rounded-md bg-red-50 p-2 text-xs text-red-700">
            {stage.error}
          </p>
        )}

        {stage.details?.edge_count != null && (
          <p className="mt-1 text-xs text-slate-500">
            Edges: {String(stage.details.edge_count)}
          </p>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const normalized = normalizeStatus(status);

  const statusClass = ["completed", "complete", "success"].includes(normalized)
    ? "dashboard-status-success"
    : ["processing", "running", "in_progress"].includes(normalized)
      ? "dashboard-status-running"
      : ["failed", "error"].includes(normalized)
        ? "dashboard-status-danger"
        : ["queued", "pending"].includes(normalized)
          ? "dashboard-status-warning"
          : "dashboard-status-neutral";

  return (
    <span className={`dashboard-status inline-flex items-center ${statusClass}`}>
      {formatStatus(status)}
    </span>
  );
}

function SummaryCard({ label, value, description, href, icon: Icon }: { label: string; value: string; description: string; href: string; icon: LucideIcon }) {
  return <Link href={href} className="dashboard-metric-link group block rounded-2xl focus-visible:ring-2 focus-visible:ring-cyan-300">
    <div className="dashboard-metric-card h-full rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm transition group-hover:-translate-y-1 group-hover:border-cyan-300/40">
      <div className="flex items-center justify-between"><p className="text-sm font-medium text-slate-500">{label}</p><div className="rounded-lg bg-slate-100 p-2 text-slate-600"><Icon size={18}/></div></div>
      <p className="mt-4 font-mono text-3xl font-bold tracking-tight text-slate-950">{value}</p><p className="mt-1 text-xs text-slate-500">{description}</p>
      <p className="mt-3 text-[10px] font-semibold uppercase tracking-wider text-cyan-300">Open workspace ↗</p>
    </div>
  </Link>;
}

export default function DashboardData() {
  const [data, setData] = useState<DashboardDataState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [drawingsRefreshing, setDrawingsRefreshing] = useState(false);
  const [jobsRefreshing, setJobsRefreshing] = useState(false);
  const [sectionErrors, setSectionErrors] = useState<{
    drawings: string | null;
    jobs: string | null;
  }>({
    drawings: null,
    jobs: null,
  });

  const [pipelineProgress, setPipelineProgress] =
    useState<StageProgress | null>(null);

  const [pipelineLoading, setPipelineLoading] = useState(false);
  const [pipelineError, setPipelineError] = useState<string | null>(null);
  const [pipelineRetryKey, setPipelineRetryKey] = useState(0);

  useEffect(() => {
    let active = true;

    async function loadDashboardData() {
      try {
        setLoading(true);
        setError(null);

        const projects = await projectsApi.getProjects();

        const warnings: string[] = [];

        const drawingResults = await Promise.allSettled(
          projects.map((project) =>
            drawingsApi.getProjectDrawings(project.id)
          )
        );

        const allDrawings: DashboardDrawing[] = [];
        let drawingTotal = 0;

        drawingResults.forEach((result, index) => {
          const project = projects[index];

          if (result.status === "rejected") {
            warnings.push(
              `Could not load drawings for project "${project.name}".`
            );
            return;
          }

          drawingTotal += result.value.total;

          result.value.items.forEach((drawing) => {
            allDrawings.push({
              ...drawing,
              project_name: project.name,
            });
          });
        });

        allDrawings.sort(
          (a, b) =>
            new Date(b.created_at).getTime() -
            new Date(a.created_at).getTime()
        );

        // Retrieve job history in small batches.
        // A failed drawing request will not block other drawings.
        const allJobs: DashboardJob[] = [];
        let jobTotal = 0;
        const batchSize = 8;

        for (let i = 0; i < allDrawings.length; i += batchSize) {
          const batch = allDrawings.slice(i, i + batchSize);

          const results = await Promise.allSettled(
            batch.map((drawing) =>
              processingApi.getDrawingJobs(drawing.id)
            )
          );

          results.forEach((result, index) => {
            const drawing = batch[index];

            if (result.status === "rejected") {
              warnings.push(
                `Could not load processing history for "${drawing.original_filename}".`
              );
              return;
            }

            jobTotal += result.value.total;

            result.value.items.forEach((job) => {
              allJobs.push({
                ...job,
                drawing_name: drawing.original_filename,
                project_name: drawing.project_name,
              });
            });
          });
        }

        allJobs.sort(
          (a, b) =>
            new Date(b.created_at).getTime() -
            new Date(a.created_at).getTime()
        );

        if (active) {
          setData({
            projects,
            allDrawings,
            drawings: allDrawings.slice(0, 5),
            drawingTotal,
            jobs: allJobs,
            jobTotal,
            warnings,
          });
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error
              ? err.message
              : "Unable to load dashboard data."
          );
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadDashboardData();

    return () => {
      active = false;
    };
  }, []);

  async function refreshDrawings() {
    if (!data || drawingsRefreshing) return;

    setDrawingsRefreshing(true);
    setSectionErrors((previous) => ({
      ...previous,
      drawings: null,
    }));

    try {
      const results = await Promise.allSettled(
        data.projects.map((project) =>
          drawingsApi.getProjectDrawings(project.id)
        )
      );

      const updatedDrawings: DashboardDrawing[] = [];
      let drawingTotal = 0;
      const warnings: string[] = [];

      results.forEach((result, index) => {
        const project = data.projects[index];

        if (result.status === "rejected") {
          warnings.push(
            `Could not load drawings for project "${project.name}".`
          );
          return;
        }

        drawingTotal += result.value.total;

        result.value.items.forEach((drawing) => {
          updatedDrawings.push({
            ...drawing,
            project_name: project.name,
          });
        });
      });

      // If any project failed, preserve its previous drawings.
      results.forEach((result, index) => {
        if (result.status !== "rejected") return;

        const project = data.projects[index];

        data.allDrawings
          .filter((drawing) => drawing.project_id === project.id)
          .forEach((drawing) => {
            updatedDrawings.push(drawing);
            drawingTotal += 1;
          });
      });

      updatedDrawings.sort(
        (a, b) =>
          new Date(b.created_at).getTime() -
          new Date(a.created_at).getTime()
      );

      setData((previous) =>
        previous
          ? {
              ...previous,
              allDrawings: updatedDrawings,
              drawings: updatedDrawings.slice(0, 5),
              drawingTotal,
              warnings: [
                ...previous.warnings.filter(
                  (warning) =>
                    !warning.startsWith("Could not load drawings for project")
                ),
                ...warnings,
              ],
            }
          : previous
      );
    } catch {
      setSectionErrors((previous) => ({
        ...previous,
        drawings: "Unable to refresh drawings. Please try again.",
      }));
    } finally {
      setDrawingsRefreshing(false);
    }
  }

  async function refreshJobs() {
    if (!data || jobsRefreshing) return;

    setJobsRefreshing(true);
    setSectionErrors((previous) => ({
      ...previous,
      jobs: null,
    }));

    try {
      const allJobs: DashboardJob[] = [];
      const warnings: string[] = [];
      let jobTotal = 0;
      const batchSize = 8;

      for (let i = 0; i < data.allDrawings.length; i += batchSize) {
        const batch = data.allDrawings.slice(i, i + batchSize);

        const results = await Promise.allSettled(
          batch.map((drawing) =>
            processingApi.getDrawingJobs(drawing.id)
          )
        );

        results.forEach((result, index) => {
          const drawing = batch[index];

          if (result.status === "rejected") {
            warnings.push(
              `Could not load processing history for "${drawing.original_filename}".`
            );
            return;
          }

          jobTotal += result.value.total;

          result.value.items.forEach((job) => {
            allJobs.push({
              ...job,
              drawing_name: drawing.original_filename,
              project_name: drawing.project_name,
            });
          });
        });
      }

      allJobs.sort(
        (a, b) =>
          new Date(b.created_at).getTime() -
          new Date(a.created_at).getTime()
      );

      setData((previous) =>
        previous
          ? {
              ...previous,
              jobs: allJobs,
              jobTotal,
              warnings: [
                ...previous.warnings.filter(
                  (warning) =>
                    !warning.startsWith("Could not load processing history for")
                ),
                ...warnings,
              ],
            }
          : previous
      );
    } catch {
      setSectionErrors((previous) => ({
        ...previous,
        jobs: "Unable to refresh processing activity. Please try again.",
      }));
    } finally {
      setJobsRefreshing(false);
    }
  }

  // Prefer the newest active job; otherwise inspect the newest job.
  const selectedPipelineJob =
    data?.jobs.find((job) => isActiveJob(job.status)) ??
    data?.jobs[0] ??
    null;

  useEffect(() => {
    if (!selectedPipelineJob) {
      setPipelineProgress(null);
      setPipelineError(null);
      setPipelineLoading(false);
      return;
    }

    let active = true;

    const loadProgress = async () => {
      try {
        const response =
          await processingApi.getProcessingJobProgress(
            selectedPipelineJob.id
          );

        if (active) {
          setPipelineProgress(response.stage_progress);
          setPipelineError(null);
          setPipelineLoading(false);
        }
      } catch (err) {
        if (active) {
          setPipelineError(
            err instanceof Error
              ? err.message
              : "Unable to load pipeline progress."
          );
          setPipelineLoading(false);
        }
      }
    };

    setPipelineLoading(true);
    setPipelineProgress(null);
    setPipelineError(null);

    void loadProgress();

    // Refresh only while this job is active.
    const timer = isActiveJob(selectedPipelineJob.status)
      ? window.setInterval(() => {
          void loadProgress();
        }, 3000)
      : null;

    return () => {
      active = false;

      if (timer !== null) {
        window.clearInterval(timer);
      }
    };
  }, [
    selectedPipelineJob?.id,
    selectedPipelineJob?.status,
    pipelineRetryKey,
  ]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {[1, 2, 3, 4].map((item) => (
            <div
              key={item}
              className="h-32 animate-pulse rounded-xl border bg-white"
            />
          ))}
        </div>
        <div className="h-64 animate-pulse rounded-xl border bg-white" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-5">
        <p className="font-semibold text-red-800">
          Dashboard data could not be loaded
        </p>
        <p className="mt-1 text-sm text-red-700">
          {error ?? "No dashboard data is available."}
        </p>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="mt-3 rounded-lg border border-red-300 px-3 py-2 text-sm font-medium text-red-800 hover:bg-red-100"
        >
          Retry
        </button>
      </div>
    );
  }

  const countStatuses = (accepted: string[]) =>
    data.jobs.filter((job) =>
      accepted.includes(normalizeStatus(job.status))
    ).length;

  const queued = countStatuses(["queued", "pending"]);
  const running = countStatuses(["processing", "running", "in_progress"]);
  const completed = countStatuses(["completed", "complete", "success"]);
  const failed = countStatuses(["failed", "error"]);

  return (
    <div className="space-y-6">
      {data.warnings.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
          <div className="flex items-start gap-2">
            <AlertCircle
              className="mt-0.5 shrink-0 text-amber-600"
              size={18}
            />

            <div>
              <p className="text-sm font-semibold text-amber-900">
                Some dashboard information could not be loaded
              </p>

              <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-amber-800">
                {data.warnings.map((warning, index) => (
                  <li key={index}>{warning}</li>
                ))}
              </ul>

              <button
                type="button"
                onClick={() => window.location.reload()}
                className="mt-3 text-xs font-semibold text-amber-900 underline"
              >
                Reload dashboard
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Summary metrics */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <SummaryCard
          label="Projects"
          value={String(data.projects.length)}
          description="Projects in your workspace"
          icon={FolderKanban}
          href="/projects"
        />

        <SummaryCard
          label="DXF drawings"
          value={String(data.drawingTotal)}
          description="Drawings across all projects"
          icon={FileCode2}
          href="/drawings"
        />

        <SummaryCard
          label="Processing jobs"
          value={String(data.jobTotal)}
          description={`${queued} queued · ${running} running`}
          icon={Workflow}
          href="/pipeline"
        />

        <SummaryCard
          label="BOM items"
          value="—"
          description="BOM summary not yet exposed by API"
          icon={Box}
          href="/projects"
        />
      </div>

      {/* Operational status at a glance */}
      <section aria-label="Processing status overview" className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        {[
          { label: "Queued", value: queued, marker: "bg-amber-300" },
          { label: "Running", value: running, marker: "bg-blue-300" },
          { label: "Completed", value: completed, marker: "bg-emerald-300" },
          { label: "Failed", value: failed, marker: "bg-rose-300" },
        ].map((item) => (
          <div key={item.label} className="dashboard-subpanel flex items-center justify-between px-4 py-3">
            <div className="flex items-center gap-2.5">
              <span className={`h-2 w-2 rounded-full ${item.marker}`} />
              <span className="text-xs font-medium text-slate-400">{item.label}</span>
            </div>
            <span className="font-mono text-lg font-semibold text-slate-100">{item.value}</span>
          </div>
        ))}
      </section>

      {/* Project execution overview */}
      <section className="dashboard-panel p-5 md:p-6">
        <div className="mb-5 flex items-end justify-between gap-3"><div><p className="mb-1 text-[10px] font-bold uppercase tracking-[.16em] text-cyan-300">Project operations</p><h3 className="font-semibold text-slate-100">Project progress</h3><p className="mt-1 text-xs text-slate-400">Calculated from completed processing jobs reported for each project.</p></div><Link href="/projects" className="text-xs font-semibold text-cyan-300">All projects ↗</Link></div>
        <div className="grid gap-3 xl:grid-cols-2">
          {data.projects.map((project) => {
            const projectJobs = data.jobs.filter((job) => data.allDrawings.some((drawing) => drawing.id === job.drawing_id && drawing.project_id === project.id));
            const done = projectJobs.filter((job) => ["completed", "complete", "success"].includes(normalizeStatus(job.status))).length;
            const activeJobs = projectJobs.filter((job) => isActiveJob(job.status)).length;
            const failedJobs = projectJobs.filter((job) => ["failed", "error"].includes(normalizeStatus(job.status))).length;
            const percent = projectJobs.length ? Math.round(done / projectJobs.length * 100) : 0;
            const drawingCount = data.allDrawings.filter((drawing) => drawing.project_id === project.id).length;
            return <Link key={project.id} href={'/drawings?projectId=' + encodeURIComponent(project.id)} className="dashboard-project-card group rounded-xl border border-white/[.08] bg-[#0d192a]/70 p-4 transition hover:border-cyan-300/30 hover:bg-[#12233a]">
              <div className="flex items-start justify-between"><div><p className="text-sm font-semibold text-slate-100 group-hover:text-cyan-200">{project.name}</p><p className="mt-1 text-[11px] text-slate-500">{drawingCount} drawings · {projectJobs.length} jobs</p></div><FolderKanban size={17} className="text-cyan-200"/></div>
              <div className="mt-4 flex justify-between text-[11px]"><span className="text-slate-400">{projectJobs.length ? done + ' of ' + projectJobs.length + ' jobs completed' : 'Awaiting first processing run'}</span><span className="font-mono text-slate-200">{projectJobs.length ? percent + '%' : '—'}</span></div>
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/[.07]"><div className="h-full rounded-full bg-gradient-to-r from-blue-400 to-cyan-300" style={{width: percent + '%'}}/></div>
              <div className="mt-3 flex gap-3 text-[10px]"><span className="text-emerald-300">{done} completed</span><span className="text-blue-300">{activeJobs} active</span><span className={failedJobs ? 'text-rose-300' : 'text-slate-500'}>{failedJobs} failed</span></div>
            </Link>;
          })}
        </div>
      </section>

      {/* Failed job monitoring */}
      <section className="dashboard-panel p-5 md:p-6">
        <div className="mb-4 flex items-center justify-between"><div><p className="mb-1 text-[10px] font-bold uppercase tracking-[.16em] text-rose-300">Attention required</p><h3 className="font-semibold text-slate-100">Failed job monitoring</h3><p className="mt-1 text-xs text-slate-400">Recent failed processing attempts requiring review.</p></div><Link href="/pipeline" className="text-xs font-semibold text-cyan-300">Open job monitor ↗</Link></div>
        {data.jobs.filter((job) => ['failed', 'error'].includes(normalizeStatus(job.status))).length ? <div className="space-y-2">{data.jobs.filter((job) => ['failed', 'error'].includes(normalizeStatus(job.status))).slice(0,4).map((job) => <Link key={job.id} href={'/pipeline?jobId=' + encodeURIComponent(job.id)} className="flex flex-col gap-1 rounded-xl border border-rose-400/15 bg-rose-400/[.045] p-3 transition hover:border-rose-300/35 sm:flex-row sm:items-center sm:justify-between"><div><p className="text-sm font-medium text-slate-100">{job.drawing_name}</p><p className="mt-1 text-[11px] text-slate-400">{job.project_name} · {formatDate(job.created_at)}</p><p className="mt-1 text-xs text-rose-200/80">{job.error_message || 'Processing failed. Open the job monitor for diagnostics.'}</p></div><span className="text-xs font-semibold text-rose-300">Inspect job ↗</span></Link>)}</div> : <div className="flex items-center gap-3 rounded-xl border border-emerald-400/15 bg-emerald-400/[.045] p-4"><CheckCircle2 size={19} className="text-emerald-300"/><div><p className="text-sm font-medium text-emerald-200">No failed jobs reported</p><p className="mt-1 text-xs text-slate-400">No failed processing attempts in the loaded history.</p></div></div>}
      </section>

      {/* BOM generation visibility */}
      <section className="dashboard-panel flex flex-col gap-3 p-5 md:flex-row md:items-center md:justify-between"><div><p className="mb-1 text-[10px] font-bold uppercase tracking-[.16em] text-violet-300">BOM intelligence</p><h3 className="font-semibold text-slate-100">BOM generation overview</h3><p className="mt-1 text-xs text-slate-400">Aggregate BOM item counts are not exposed by the current dashboard API. Continue through a project to inspect its drawing workflow.</p></div><Link href="/projects" className="text-xs font-semibold text-violet-200">Explore projects ↗</Link></section>

      {/* Recent drawings */}
      <div className="dashboard-panel rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm shadow-slate-200/40">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="font-semibold">Recent drawings</h3>
            <p className="mt-1 text-xs text-slate-500">
              Latest uploaded drawings across your projects
            </p>
          </div>
          {sectionErrors.drawings && (
            <p className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">
              {sectionErrors.drawings}
            </p>
          )}
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={refreshDrawings}
              disabled={drawingsRefreshing}
              className="text-sm font-medium text-slate-600 hover:text-blue-700 disabled:opacity-50"
            >
              {drawingsRefreshing ? "Refreshing..." : "Refresh"}
            </button>

            <a
              href="/drawings"
              className="text-sm font-medium text-blue-600 hover:text-blue-700"
            >
              View all
            </a>
          </div>
        </div>

        {data.drawings.length === 0 ? (
          <div className="rounded-lg border border-dashed border-slate-200 py-10 text-center">
            <FileCode2 className="mx-auto mb-3 text-slate-400" size={28} />
            <p className="text-sm font-medium text-slate-700">
              No drawings uploaded yet
            </p>
            <p className="mt-1 text-xs text-slate-500">
              Upload a DXF drawing to one of your projects to get started.
            </p>
            <a
              href="/drawings"
              className="mt-4 inline-flex rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Go to drawings
            </a>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[620px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-xs text-slate-400">
                  <th className="pb-3 font-medium">Drawing</th>
                  <th className="pb-3 font-medium">Project</th>
                  <th className="pb-3 font-medium">Status</th>
                  <th className="pb-3 font-medium">Uploaded</th>
                </tr>
              </thead>
              <tbody>
                {data.drawings.map((drawing) => (
                  <tr
                    key={drawing.id}
                    className="border-b border-slate-50 last:border-0"
                  >
                    <td className="py-4 pr-4">
                      <Link href={"/drawings?projectId=" + encodeURIComponent(drawing.project_id)} className="flex items-center gap-3">
                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
                          <FileCode2 size={18} />
                        </div>
                        <div className="min-w-0">
                          <p className="truncate font-medium text-slate-800">
                            {drawing.original_filename}
                          </p>
                          <p className="mt-1 text-xs text-slate-400">
                            {(drawing.file_size / (1024 * 1024)).toFixed(2)} MB
                          </p>
                        </div>
                      </Link>
                    </td>
                    <td className="py-4 pr-4 text-slate-600">
                      <Link href="/projects">{drawing.project_name}</Link>
                    </td>
                    <td className="py-4 pr-4">
                      <StatusBadge status={drawing.status} />
                    </td>
                    <td className="py-4 text-slate-500">
                      {formatDate(drawing.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Recent processing jobs */}
      <div className="dashboard-panel rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm shadow-slate-200/40">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="font-semibold">Recent processing activity</h3>
            <p className="mt-1 text-xs text-slate-500">
              Latest processing attempts across your drawings
            </p>
          </div>
          {sectionErrors.jobs && (
            <p className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">
              {sectionErrors.jobs}
            </p>
          )}
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={refreshJobs}
              disabled={jobsRefreshing}
              className="text-sm font-medium text-slate-600 hover:text-blue-700 disabled:opacity-50"
            >
              {jobsRefreshing ? "Refreshing..." : "Refresh"}
            </button>

            <a
              href="/pipeline"
              className="text-sm font-medium text-blue-600 hover:text-blue-700"
            >
              View pipeline
            </a>
          </div>
        </div>

        <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { label: "Queued", value: queued },
            { label: "Running", value: running },
            { label: "Completed", value: completed },
            { label: "Failed", value: failed },
          ].map((item) => (
            <div
              key={item.label}
              className="rounded-lg bg-slate-50 p-3"
            >
              <p className="text-xs text-slate-500">{item.label}</p>
              <p className="mt-1 text-xl font-semibold">{item.value}</p>
            </div>
          ))}
        </div>

        {data.jobs.length === 0 ? (
          <div className="rounded-lg border border-dashed border-slate-200 py-8 text-center">
            <Workflow className="mx-auto mb-3 text-slate-400" size={26} />
            <p className="text-sm font-medium text-slate-700">
              No processing jobs yet
            </p>
            <p className="mt-1 text-xs text-slate-500">
              Submit a drawing for processing to see activity here.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[600px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-xs text-slate-400">
                  <th className="pb-3 font-medium">Drawing</th>
                  <th className="pb-3 font-medium">Project</th>
                  <th className="pb-3 font-medium">Status</th>
                  <th className="pb-3 font-medium">Submitted</th>
                </tr>
              </thead>
              <tbody>
                {data.jobs.slice(0, 5).map((job) => (
                  <tr
                    key={job.id}
                    className="border-b border-slate-50 last:border-0"
                  >
                    <td className="py-4 pr-4">
                      <Link href={"/pipeline?jobId=" + encodeURIComponent(job.id)} className="block"><p className="font-medium text-slate-800 hover:text-cyan-300">
                        {job.drawing_name}
                      </p>
                      <p className="mt-1 text-xs text-slate-400">
                        Attempt count: {job.attempt_count}
                      </p></Link>
                    </td>
                    <td className="py-4 pr-4 text-slate-600">
                      <Link href="/projects">{job.project_name}</Link>
                    </td>
                    <td className="py-4 pr-4">
                      <StatusBadge status={job.status} />
                    </td>
                    <td className="py-4 text-slate-500">
                      {formatDate(job.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Live analysis pipeline */}
      <div className="dashboard-panel rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm shadow-slate-200/40">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="font-semibold">Analysis pipeline</h3>
            <p className="mt-1 text-xs text-slate-500">
              Actual execution stages from the selected processing job
            </p>
          </div>

          <a
            href="/pipeline"
            className="text-sm font-medium text-blue-600 hover:text-blue-700"
          >
            View full pipeline
          </a>
        </div>

        {!selectedPipelineJob ? (
          <div className="rounded-lg border border-dashed border-slate-200 py-8 text-center">
            <Workflow className="mx-auto mb-3 text-slate-400" size={26} />
            <p className="text-sm font-medium text-slate-700">
              No processing job available
            </p>
            <p className="mt-1 text-xs text-slate-500">
              Submit a drawing for processing to see its execution stages.
            </p>
          </div>
        ) : (
          <>
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-lg bg-slate-50 p-3">
              <div>
                <p className="text-sm font-medium text-slate-800">
                  {selectedPipelineJob.drawing_name}
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  {selectedPipelineJob.project_name}
                </p>
              </div>

              <StatusBadge status={selectedPipelineJob.status} />
            </div>

            {pipelineLoading && !pipelineProgress ? (
              <div className="flex items-center gap-2 py-6 text-sm text-slate-500">
                <LoaderCircle className="animate-spin" size={18} />
                Loading execution progress...
              </div>
            ) : pipelineError && !pipelineProgress ? (
              <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">
                <p className="font-medium">
                  Pipeline progress could not be loaded
                </p>

                <p className="mt-1">{pipelineError}</p>

                <button
                  type="button"
                  onClick={() => setPipelineRetryKey((key) => key + 1)}
                  disabled={pipelineLoading}
                  className="mt-3 rounded-lg border border-red-300 px-3 py-2 text-xs font-medium hover:bg-red-100 disabled:opacity-50"
                >
                  Retry
                </button>
              </div>
            ) : !pipelineProgress ||
              pipelineProgress.stages.length === 0 ? (
              <div className="rounded-lg border border-dashed border-slate-200 py-8 text-center">
                <Clock3 className="mx-auto mb-3 text-slate-400" size={24} />
                <p className="text-sm font-medium text-slate-700">
                  No stage events recorded yet
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  The pipeline has not reported any stage progress for this job.
                </p>
              </div>
            ) : (
              <>
                <div className="mb-4 flex flex-wrap items-center gap-4 text-xs text-slate-500">
                  <span>
                    Overall status:{" "}
                    <strong className="text-slate-700">
                      {formatStatus(pipelineProgress.overall_status)}
                    </strong>
                  </span>

                  {pipelineProgress.current_stage && (
                    <span>
                      Current stage:{" "}
                      <strong className="text-slate-700">
                        {formatStageName(pipelineProgress.current_stage)}
                      </strong>
                    </span>
                  )}
                </div>

                <div className="mb-5 rounded-xl border border-cyan-300/10 bg-cyan-300/[0.035] p-4">
                  <div className="mb-2 flex items-center justify-between gap-3">
                    <span className="text-xs font-semibold text-slate-200">CAD analysis execution</span>
                    <span className="font-mono text-xs text-cyan-200">
                      {pipelineProgress.stages.filter((stage) => ["completed", "complete", "success"].includes(normalizeStatus(stage.status))).length} / {pipelineProgress.stages.length} stages
                    </span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-white/[0.07]">
                    <div className="h-full rounded-full bg-gradient-to-r from-blue-400 via-cyan-300 to-emerald-300 transition-all duration-700" style={{ width: (pipelineProgress.stages.filter((stage) => ["completed", "complete", "success"].includes(normalizeStatus(stage.status))).length / pipelineProgress.stages.length * 100) + "%" }} />
                  </div>
                </div>
                <div>
                  {pipelineProgress.stages.map((stage) => (
                    <StageProgressRow
                      key={stage.name}
                      stage={stage}
                    />
                  ))}
                </div>

                {pipelineProgress.error && (
                  <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">
                    {pipelineProgress.error}
                  </div>
                )}

                {pipelineError && (
                  <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-amber-700">
                    <span>Latest refresh failed: {pipelineError}</span>

                    <button
                      type="button"
                      onClick={() => setPipelineRetryKey((key) => key + 1)}
                      disabled={pipelineLoading}
                      className="font-semibold underline disabled:opacity-50"
                    >
                      Retry
                    </button>
                  </div>
                )}
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}