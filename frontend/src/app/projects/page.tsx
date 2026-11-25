"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  FolderKanban,
  Plus,
  RefreshCw,
  Upload,
  FileText,
} from "lucide-react";

import { projectsApi } from "@/lib/api";

import { Project } from "@/types/project";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadProjects = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const result = await projectsApi.getProjects();
      setProjects(result);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not load projects.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadProjects();
  }, [loadProjects]);

  async function handleCreateProject(
    event: React.FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (!name.trim()) {
      setError("Enter a project name.");
      return;
    }

    setCreating(true);
    setError("");
    setSuccess("");

    try {
      const project = await projectsApi.createProject({
        name: name.trim(),
        description: description.trim() || null,
      });

      setProjects((current) => [project, ...current]);
      setName("");
      setDescription("");
      setSuccess(`Project "${project.name}" created successfully.`);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not create project.",
      );
    } finally {
      setCreating(false);
    }
  }

  return (
    <main className="min-h-screen space-y-8 p-6 md:p-8">
      <div>
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to dashboard
        </Link>

        <div className="mt-4 flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <FolderKanban className="h-4 w-4" />
              Workspace
            </div>
            <h1 className="mt-2 text-3xl font-bold tracking-tight">
              Projects
            </h1>
            <p className="mt-2 text-muted-foreground">
              Manage structural steel projects and their DXF drawings.
            </p>
          </div>

          <button
            type="button"
            onClick={() => void loadProjects()}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium hover:bg-muted disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
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
          {success}
        </div>
      )}

      <section className="rounded-xl border bg-card p-6">
        <div className="mb-5 flex items-center gap-2">
          <Plus className="h-5 w-5" />
          <h2 className="text-lg font-semibold">Create a project</h2>
        </div>

        <form onSubmit={handleCreateProject} className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <label htmlFor="project-name" className="text-sm font-medium">
              Project name *
            </label>
            <input
              id="project-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="e.g. Industrial Steel Platform"
              required
              maxLength={200}
              className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
            />
          </div>

          <div className="space-y-2">
            <label
              htmlFor="project-description"
              className="text-sm font-medium"
            >
              Description
            </label>
            <input
              id="project-description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Optional project description"
              className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
            />
          </div>

          <div className="md:col-span-2">
            <button
              type="submit"
              disabled={creating || !name.trim()}
              className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Plus className="h-4 w-4" />
              {creating ? "Creating..." : "Create project"}
            </button>
          </div>
        </form>
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">Your projects</h2>
          <span className="text-sm text-muted-foreground">
            {projects.length} project{projects.length === 1 ? "" : "s"}
          </span>
        </div>

        {loading ? (
          <div className="rounded-xl border p-8 text-center text-muted-foreground">
            Loading projects...
          </div>
        ) : projects.length === 0 ? (
          <div className="rounded-xl border border-dashed p-10 text-center">
            <FolderKanban className="mx-auto h-10 w-10 text-muted-foreground" />
            <h3 className="mt-4 font-semibold">No projects yet</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Create your first project above to start uploading DXF drawings.
            </p>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {projects.map((project) => (
              <article
                key={project.id}
                className="rounded-xl border bg-card p-5 transition hover:border-primary/50"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="rounded-lg bg-primary/10 p-3">
                    <FolderKanban className="h-5 w-5 text-primary" />
                  </div>
                  <span className="rounded-full bg-muted px-2.5 py-1 text-xs text-muted-foreground">
                    Project
                  </span>
                </div>

                <h3 className="mt-4 truncate text-lg font-semibold">
                  {project.name}
                </h3>

                <p className="mt-2 min-h-10 text-sm text-muted-foreground">
                  {project.description || "No description provided."}
                </p>

                <p className="mt-3 text-xs text-muted-foreground">
                  Created{" "}
                  {new Date(project.created_at).toLocaleDateString()}
                </p>

                <div className="mt-5 flex flex-wrap gap-2">
                  <Link
                    href={`/drawings?projectId=${encodeURIComponent(project.id)}`}
                    className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
                  >
                    <Upload className="h-4 w-4" />
                    Open drawings
                  </Link>

                  <span className="inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-xs text-muted-foreground">
                    <FileText className="h-4 w-4" />
                    {project.id.slice(0, 8)}
                  </span>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}