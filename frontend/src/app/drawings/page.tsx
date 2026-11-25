"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  FileUp,
  FileText,
  RefreshCw,
  Play,
  FolderKanban,
  Loader2,
  CheckCircle2,
} from "lucide-react";

import { drawingsApi, processingApi, projectsApi } from "@/lib/api";
import { Project } from "@/types/project";
import { Drawing } from "@/types/drawing";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function formatDate(value: string): string {
  return new Date(value).toLocaleString();
}

export default function DrawingsPage() {
  const router = useRouter();

  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [drawings, setDrawings] = useState<Drawing[]>([]);
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [loadingDrawings, setLoadingDrawings] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadDrawings = useCallback(async (projectId: string) => {
    if (!projectId) {
      setDrawings([]);
      return;
    }

    setLoadingDrawings(true);
    setError("");

    try {
      const result = await drawingsApi.getProjectDrawings(projectId);
      setDrawings(result.items);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not load drawings.",
      );
    } finally {
      setLoadingDrawings(false);
    }
  }, []);

  useEffect(() => {
    let active = true;

    async function initialize() {
      setLoadingProjects(true);
      setError("");

      try {
        const result = await projectsApi.getProjects();

        if (!active) return;

        setProjects(result);

        const queryProjectId = new URLSearchParams(
          window.location.search,
        ).get("projectId");

        const initialProjectId =
          result.find((project) => project.id === queryProjectId)?.id ??
          result[0]?.id ??
          "";

        setSelectedProjectId(initialProjectId);
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error ? err.message : "Could not load projects.",
          );
        }
      } finally {
        if (active) setLoadingProjects(false);
      }
    }

    void initialize();

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (selectedProjectId) {
      void loadDrawings(selectedProjectId);
    } else {
      setDrawings([]);
    }
  }, [selectedProjectId, loadDrawings]);

  async function handleUpload(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedProjectId) {
      setError("Select a project before uploading.");
      return;
    }

    if (!selectedFile) {
      setError("Choose a DXF file to upload.");
      return;
    }

    if (!selectedFile.name.toLowerCase().endsWith(".dxf")) {
      setError("Only .dxf files are accepted by this upload form.");
      return;
    }

    setUploading(true);
    setError("");
    setSuccess("");

    try {
      const drawing = await drawingsApi.uploadDrawing(selectedProjectId, selectedFile);

      setDrawings((current) => [drawing, ...current]);
      setSelectedFile(null);

      const fileInput = document.getElementById(
        "dxf-file",
      ) as HTMLInputElement | null;

      if (fileInput) fileInput.value = "";

      setSuccess(`Uploaded "${drawing.original_filename}" successfully.`);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "DXF upload failed.",
      );
    } finally {
      setUploading(false);
    }
  }

  async function handleProcess(drawing: Drawing) {
    setProcessingId(drawing.id);
    setError("");
    setSuccess("");

    try {
      const job = await processingApi.submitDrawingProcessing(drawing.id);

      if (!job.id) {
        throw new Error(
          "The processing API did not return a job ID.",
        );
      }

      router.push(`/pipeline?jobId=${encodeURIComponent(job.id)}`);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not submit drawing for processing.",
      );
    } finally {
      setProcessingId(null);
    }
  }

  const selectedProject = projects.find(
    (project) => project.id === selectedProjectId,
  );

  return (
    <main className="min-h-screen space-y-8 p-6 md:p-8">
      <div>
        <Link
          href="/projects"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to projects
        </Link>

        <div className="mt-4 flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <FileText className="h-4 w-4" />
              Drawing management
            </div>
            <h1 className="mt-2 text-3xl font-bold tracking-tight">
              DXF Drawings
            </h1>
            <p className="mt-2 text-muted-foreground">
              Upload engineering drawings and start the processing pipeline.
            </p>
          </div>

          <button
            type="button"
            onClick={() => void loadDrawings(selectedProjectId)}
            disabled={!selectedProjectId || loadingDrawings}
            className="inline-flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium hover:bg-muted disabled:opacity-50"
          >
            <RefreshCw
              className={`h-4 w-4 ${loadingDrawings ? "animate-spin" : ""}`}
            />
            Refresh drawings
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-800">
          {error}
        </div>
      )}

      {success && (
        <div className="rounded-lg border border-green-300 bg-green-50 p-4 text-sm text-green-800">
          <span className="inline-flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4" />
            {success}
          </span>
        </div>
      )}

      <section className="rounded-xl border bg-card p-6">
        <div className="mb-4 flex items-center gap-2">
          <FolderKanban className="h-5 w-5" />
          <h2 className="text-lg font-semibold">Select project</h2>
        </div>

        {loadingProjects ? (
          <p className="text-sm text-muted-foreground">
            Loading projects...
          </p>
        ) : projects.length === 0 ? (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              You need to create a project before uploading drawings.
            </p>
            <Link
              href="/projects"
              className="inline-flex rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
            >
              Create a project
            </Link>
          </div>
        ) : (
          <>
            <select
              value={selectedProjectId}
              onChange={(event) => {
                setSelectedProjectId(event.target.value);
                setSuccess("");
              }}
              className="w-full max-w-xl rounded-lg border bg-background px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-ring"
            >
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>

            {selectedProject && (
              <p className="mt-2 text-sm text-muted-foreground">
                {selectedProject.description || "No project description."}
              </p>
            )}
          </>
        )}
      </section>

      <section className="rounded-xl border bg-card p-6">
        <div className="mb-5 flex items-center gap-2">
          <FileUp className="h-5 w-5" />
          <h2 className="text-lg font-semibold">Upload DXF drawing</h2>
        </div>

        <form onSubmit={handleUpload} className="space-y-4">
          <div className="rounded-xl border-2 border-dashed p-6 text-center">
            <FileUp className="mx-auto h-9 w-9 text-muted-foreground" />

            <label
              htmlFor="dxf-file"
              className="mt-3 block cursor-pointer font-medium"
            >
              Choose a DXF file
            </label>

            <p className="mt-1 text-sm text-muted-foreground">
              Select an AutoCAD DXF drawing from your computer.
            </p>

            <input
              id="dxf-file"
              type="file"
              accept=".dxf,application/dxf,application/octet-stream"
              onChange={(event) =>
                setSelectedFile(event.target.files?.[0] ?? null)
              }
              className="mx-auto mt-4 block max-w-full text-sm"
            />

            {selectedFile && (
              <p className="mt-3 text-sm font-medium">
                {selectedFile.name} · {formatFileSize(selectedFile.size)}
              </p>
            )}
          </div>

          <button
            type="submit"
            disabled={
              uploading ||
              !selectedProjectId ||
              !selectedFile ||
              loadingProjects
            }
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {uploading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <FileUp className="h-4 w-4" />
            )}
            {uploading ? "Uploading..." : "Upload drawing"}
          </button>
        </form>
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold">Uploaded drawings</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {selectedProject?.name ?? "Select a project"} ·{" "}
              {drawings.length} drawing{drawings.length === 1 ? "" : "s"}
            </p>
          </div>
        </div>

        {loadingDrawings ? (
          <div className="rounded-xl border p-8 text-center text-muted-foreground">
            Loading drawings...
          </div>
        ) : drawings.length === 0 ? (
          <div className="rounded-xl border border-dashed p-10 text-center">
            <FileText className="mx-auto h-10 w-10 text-muted-foreground" />
            <h3 className="mt-4 font-semibold">No drawings uploaded</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Upload a DXF file above to begin.
            </p>
          </div>
        ) : (
          <div className="overflow-hidden rounded-xl border">
            <div className="divide-y">
              {drawings.map((drawing) => (
                <article
                  key={drawing.id}
                  className="flex flex-col gap-4 p-4 md:flex-row md:items-center md:justify-between"
                >
                  <div className="flex min-w-0 items-start gap-3">
                    <div className="rounded-lg bg-primary/10 p-3">
                      <FileText className="h-5 w-5 text-primary" />
                    </div>

                    <div className="min-w-0">
                      <h3 className="truncate font-medium">
                        {drawing.original_filename}
                      </h3>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {formatFileSize(drawing.file_size)} ·{" "}
                        {drawing.mime_type}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Uploaded {formatDate(drawing.created_at)}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Drawing ID: {drawing.id}
                      </p>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-3">
                    <span className="rounded-full bg-muted px-3 py-1 text-xs font-medium">
                      {drawing.status}
                    </span>

                    <button
                      type="button"
                      onClick={() => void handleProcess(drawing)}
                      disabled={processingId !== null}
                      className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {processingId === drawing.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Play className="h-4 w-4" />
                      )}
                      {processingId === drawing.id
                        ? "Submitting..."
                        : "Process drawing"}
                    </button>
                  </div>
                </article>
              ))}
            </div>
          </div>
        )}
      </section>
    </main>
  );
}