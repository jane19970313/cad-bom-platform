"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  ArrowRight, ArrowUpRight, CalendarDays, FileCode2, FolderKanban,
  FolderOpen, Layers3, Plus, RefreshCw, Search, Sparkles, Trash2, X,
} from "lucide-react";
import { projectsApi } from "@/lib/api";
import type { Project } from "@/types/project";

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Date unavailable";
  return new Intl.DateTimeFormat(undefined, { year: "numeric", month: "short", day: "numeric" }).format(date);
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<Project | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadProjects = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setProjects(await projectsApi.getProjects());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load projects.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void loadProjects(); }, [loadProjects]);

  async function createProject(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    setError("");
    setSuccess("");
    try {
      const item = await projectsApi.createProject({
        name: name.trim(),
        description: description.trim() || null,
      });
      setProjects((current) => [item, ...current]);
      setName("");
      setDescription("");
      setSuccess("Project created successfully. Your workspace is ready.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to create project.");
    } finally {
      setCreating(false);
    }
  }

  async function deleteProject(project: Project) {
    setDeleting(project.id);
    setError("");
    setSuccess("");
    try {
      await projectsApi.deleteProject(project.id);
      setProjects((current) => current.filter((item) => item.id !== project.id));
      setConfirmDelete(null);
      setSuccess(`“${project.name}” and its drawings were deleted.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to delete project.");
    } finally {
      setDeleting(null);
    }
  }

  const filtered = useMemo(() => {
    const value = query.trim().toLowerCase();
    if (!value) return projects;
    return projects.filter((project) =>
      `${project.name} ${project.description ?? ""} ${project.id}`.toLowerCase().includes(value),
    );
  }, [projects, query]);

  return (
    <main className="projects-page">
      <div className="projects-page-inner">
        <section className="projects-intro">
          <div className="projects-intro-copy">
            <div className="projects-eyebrow"><span/> PROJECT MANAGEMENT <i>/</i> ENGINEERING WORKSPACE</div>
            <h1>Project <em>Command Center</em></h1>
            <p>Bring every steel grating package into one organized workspace. Manage project scopes and move directly into drawing preparation.</p>
            <div className="projects-intro-tags">
              <span><Layers3 size={13}/> PROJECT LIBRARY</span>
              <span><FileCode2 size={13}/> DXF DRAWING SETS</span>
              <span><Sparkles size={13}/> AI-READY WORKSPACE</span>
            </div>
          </div>
          <div className="projects-intro-visual" aria-hidden="true">
            <div className="projects-orbit projects-orbit-one"/>
            <div className="projects-orbit projects-orbit-two"/>
            <div className="projects-visual-core"><FolderKanban size={35}/></div>
            <span className="projects-visual-label projects-label-top">PROJECT DATA</span>
            <span className="projects-visual-label projects-label-bottom">CAD2BOM / 01</span>
            <i className="projects-visual-node node-one"/><i className="projects-visual-node node-two"/><i className="projects-visual-node node-three"/>
          </div>
        </section>

        <section className="projects-overview-strip" aria-label="Project workspace summary">
          <div className="projects-overview-item">
            <span className="projects-overview-icon"><FolderOpen size={17}/></span>
            <div><small>PROJECTS IN LIBRARY</small><strong>{loading ? "—" : projects.length.toString().padStart(2, "0")}</strong></div>
          </div>
          <div className="projects-overview-item">
            <span className="projects-overview-icon"><FileCode2 size={17}/></span>
            <div><small>SUPPORTED DRAWING INPUT</small><strong>DXF / 2D CAD</strong></div>
          </div>
          <div className="projects-overview-note"><span/> PROJECT DATA IS STORED IN YOUR WORKSPACE</div>
        </section>

        {(error || success) && (
          <div className={`projects-feedback ${error ? "is-error" : "is-success"}`} role="status">
            <span>{error || success}</span>
            <button onClick={() => { setError(""); setSuccess(""); }} aria-label="Dismiss message"><X size={15}/></button>
          </div>
        )}

        <div className="projects-main-grid">
          <section className="projects-library">
            <div className="projects-section-head">
              <div>
                <div className="projects-section-kicker">YOUR ENGINEERING DATA</div>
                <h2>Project library <span>{projects.length}</span></h2>
                <p>Select a project to manage its drawing package.</p>
              </div>
              <button className="projects-refresh" onClick={() => void loadProjects()} disabled={loading} title="Refresh projects">
                <RefreshCw size={15} className={loading ? "animate-spin" : ""}/><span>Refresh</span>
              </button>
            </div>

            <div className="projects-search-row">
              <label className="projects-search">
                <Search size={16}/>
                <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by project name, description or ID…"/>
                {query && <button type="button" onClick={() => setQuery("")} aria-label="Clear search"><X size={14}/></button>}
              </label>
              <span className="projects-result-count">{filtered.length} / {projects.length} PROJECTS</span>
            </div>

            {loading ? (
              <div className="projects-empty-state"><RefreshCw size={22} className="animate-spin"/><strong>Loading project library</strong><span>Retrieving your engineering workspaces…</span></div>
            ) : filtered.length === 0 ? (
              <div className="projects-empty-state">
                <span className="projects-empty-icon"><FolderOpen size={25}/></span>
                <strong>{projects.length ? "No matching projects" : "Your project library is ready"}</strong>
                <span>{projects.length ? "Try another search term or clear the filter." : "Create your first project to start organizing drawings."}</span>
                {query && <button onClick={() => setQuery("")}>Clear search <ArrowRight size={14}/></button>}
              </div>
            ) : (
              <div className="projects-card-grid">
                {filtered.map((project, index) => (
                  <article className="projects-card" key={project.id}>
                    <div className="projects-card-topline">
                      <span className="projects-card-number">PROJECT / {String(index + 1).padStart(2, "0")}</span>
                      <button className="projects-delete" title={`Delete ${project.name}`} onClick={() => setConfirmDelete(project)}><Trash2 size={15}/></button>
                    </div>
                    <div className="projects-card-icon"><FolderKanban size={22}/></div>
                    <h3>{project.name}</h3>
                    <p className="projects-card-description">{project.description || "No description added to this project yet."}</p>
                    <div className="projects-card-meta">
                      <span><CalendarDays size={13}/> CREATED</span><strong>{formatDate(project.created_at)}</strong>
                      <span><Layers3 size={13}/> PROJECT ID</span><strong>{project.id.slice(0, 8).toUpperCase()}</strong>
                    </div>
                    <Link href={`/drawings?projectId=${encodeURIComponent(project.id)}`} className="projects-card-action">
                      <span>Open drawing workspace</span><ArrowUpRight size={16}/>
                    </Link>
                  </article>
                ))}
              </div>
            )}
          </section>

          <aside className="projects-create-panel">
            <div className="projects-create-top">
              <span className="projects-create-icon"><Plus size={20}/></span>
              <span className="projects-create-index">NEW / 001</span>
            </div>
            <div className="projects-section-kicker">START A NEW PACKAGE</div>
            <h2>Create project</h2>
            <p className="projects-create-description">Set up a dedicated space for your steel grating drawings and BOM analysis.</p>
            <form onSubmit={createProject}>
              <label>PROJECT NAME <b>REQUIRED</b>
                <input value={name} onChange={(event) => setName(event.target.value)} placeholder="e.g. Plant Access Platform" maxLength={200} required/>
              </label>
              <label>PROJECT DESCRIPTION <i>OPTIONAL</i>
                <textarea value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Site, structure, package scope or other notes…" rows={4}/>
              </label>
              <button type="submit" className="projects-create-submit" disabled={creating || !name.trim()}>
                <Plus size={16}/>{creating ? "Creating project…" : "Create project"}<ArrowRight size={16}/>
              </button>
            </form>
            <div className="projects-create-foot"><span/> YOUR PROJECT WILL BE PRIVATE TO YOUR ACCOUNT</div>
          </aside>
        </div>
      </div>

      {confirmDelete && (
        <div className="projects-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setConfirmDelete(null); }}>
          <div className="projects-confirm-modal" role="dialog" aria-modal="true" aria-labelledby="delete-project-title">
            <span className="projects-modal-icon"><Trash2 size={20}/></span>
            <div className="projects-section-kicker">PERMANENT ACTION</div>
            <h2 id="delete-project-title">Delete this project?</h2>
            <p><strong>{confirmDelete.name}</strong> and all drawings in this project will be permanently deleted. This action cannot be undone.</p>
            <div className="projects-modal-actions">
              <button className="projects-modal-cancel" onClick={() => setConfirmDelete(null)} disabled={!!deleting}><X size={15}/> Cancel</button>
              <button className="projects-modal-delete" onClick={() => void deleteProject(confirmDelete)} disabled={!!deleting}><Trash2 size={15}/>{deleting ? "Deleting…" : "Delete project"}</button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
