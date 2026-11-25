"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, FolderKanban, Plus, RefreshCw, Trash2, Upload, Layers3, Search, X } from "lucide-react";
import { projectsApi } from "@/lib/api";
import type { Project } from "@/types/project";

export default function ProjectsPage() {
  const [projects,setProjects]=useState<Project[]>([]);
  const [name,setName]=useState("");
  const [description,setDescription]=useState("");
  const [query,setQuery]=useState("");
  const [loading,setLoading]=useState(true);
  const [creating,setCreating]=useState(false);
  const [deleting,setDeleting]=useState<string|null>(null);
  const [confirmDelete,setConfirmDelete]=useState<Project|null>(null);
  const [error,setError]=useState("");
  const [success,setSuccess]=useState("");

  const loadProjects=useCallback(async()=>{
    setLoading(true);setError("");
    try{setProjects(await projectsApi.getProjects());}
    catch(e){setError(e instanceof Error?e.message:"Unable to load projects.");}
    finally{setLoading(false);}
  },[]);
  useEffect(()=>{void loadProjects();},[loadProjects]);

  async function createProject(event:React.FormEvent<HTMLFormElement>){
    event.preventDefault();if(!name.trim())return;
    setCreating(true);setError("");setSuccess("");
    try{const item=await projectsApi.createProject({name:name.trim(),description:description.trim()||null});setProjects(v=>[item,...v]);setName("");setDescription("");setSuccess("Project created.");}
    catch(e){setError(e instanceof Error?e.message:"Unable to create project.");}
    finally{setCreating(false);}
  }
  async function deleteProject(project:Project){
    setDeleting(project.id);setError("");setSuccess("");
    try{await projectsApi.deleteProject(project.id);setProjects(v=>v.filter(p=>p.id!==project.id));setConfirmDelete(null);setSuccess(`“${project.name}” and its drawings were deleted.`);}
    catch(e){setError(e instanceof Error?e.message:"Unable to delete project.");}
    finally{setDeleting(null);}
  }
  const filtered=projects.filter(p=>`${p.name} ${p.description??""}`.toLowerCase().includes(query.toLowerCase()));

  return <main className="workspace-page min-h-screen">
    <div className="workspace-page-inner">
      <div className="workspace-breadcrumb"><Link href="/">CAD2BOM</Link><span>/</span><span>Projects</span></div>
      <header className="workspace-page-header">
        <div><div className="workspace-eyebrow"><FolderKanban size={14}/> ENGINEERING WORKSPACE</div><h1>Projects</h1><p>Organize structural steel projects and manage their drawing sets.</p></div>
        <button className="hud-button hud-button-secondary" onClick={()=>void loadProjects()} disabled={loading}><RefreshCw size={15} className={loading?"animate-spin":""}/> Refresh</button>
      </header>
      <div className="workspace-stat-strip">
        <div><span>PROJECTS</span><strong>{projects.length}</strong></div><div><span>WORKSPACE</span><strong>ACTIVE</strong></div><div><span>DRAWING FORMAT</span><strong>DXF</strong></div>
      </div>
      {error&&<div className="workspace-alert workspace-alert-error">{error}</div>}
      {success&&<div className="workspace-alert workspace-alert-success">{success}</div>}
      <section className="workspace-panel project-create-panel">
        <div className="workspace-section-heading"><div><span className="workspace-kicker">NEW WORKSPACE</span><h2>Create project</h2><p>Start a project before uploading engineering drawings.</p></div><span className="workspace-icon-tile"><Plus size={19}/></span></div>
        <form onSubmit={createProject} className="project-create-form">
          <label>Project name<input value={name} onChange={e=>setName(e.target.value)} placeholder="e.g. Industrial Steel Platform" maxLength={200} required/></label>
          <label>Description <span className="workspace-optional">OPTIONAL</span><input value={description} onChange={e=>setDescription(e.target.value)} placeholder="Project scope, site or drawing package"/></label>
          <button className="hud-button hud-button-primary" type="submit" disabled={creating||!name.trim()}><Plus size={16}/>{creating?"Creating…":"Create project"}</button>
        </form>
      </section>
      <section className="workspace-section">
        <div className="workspace-section-heading"><div><span className="workspace-kicker">PROJECT LIBRARY</span><h2>Your projects <span className="workspace-count">{projects.length}</span></h2><p>Open a project to upload, process and inspect its DXF drawings.</p></div>
          <div className="workspace-search"><Search size={15}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Find a project…"/></div>
        </div>
        {loading?<div className="workspace-empty">Loading project library…</div>:filtered.length===0?<div className="workspace-empty"><Layers3 size={30}/><h3>{projects.length?"No matching projects":"Your workspace is ready"}</h3><p>{projects.length?"Try another project name.":"Create your first project above to begin organizing drawings."}</p></div>:
          <div className="project-card-grid">{filtered.map((p,index)=><article className="project-hud-card" key={p.id}>
            <div className="project-card-top"><span className="project-card-index">{String(index+1).padStart(2,"0")}</span><span className="project-status"><i/> PROJECT</span><button className="workspace-icon-button danger" title="Delete project" onClick={()=>setConfirmDelete(p)}><Trash2 size={16}/></button></div>
            <div className="project-card-mark"><FolderKanban size={22}/></div><h3>{p.name}</h3><p className="project-card-description">{p.description||"No project description has been added."}</p>
            <div className="project-card-meta"><span>CREATED</span><strong>{new Date(p.created_at).toLocaleDateString()}</strong><span>ID</span><strong>{p.id.slice(0,8).toUpperCase()}</strong></div>
            <Link href={`/drawings?projectId=${encodeURIComponent(p.id)}`} className="project-open-link">Open drawings <ArrowUpRight size={16}/></Link>
          </article>)}</div>}
      </section>
    </div>
    {confirmDelete&&<div className="workspace-modal-backdrop" role="presentation" onMouseDown={e=>{if(e.target===e.currentTarget)setConfirmDelete(null);}}><div className="workspace-confirm-modal" role="dialog" aria-modal="true" aria-labelledby="delete-project-title"><span className="workspace-danger-icon"><Trash2 size={20}/></span><h2 id="delete-project-title">Delete project?</h2><p>“{confirmDelete.name}” and all drawings in this project will be permanently deleted. This action cannot be undone.</p><div><button className="hud-button hud-button-secondary" onClick={()=>setConfirmDelete(null)} disabled={!!deleting}><X size={15}/> Cancel</button><button className="hud-button hud-button-danger" onClick={()=>void deleteProject(confirmDelete)} disabled={!!deleting}><Trash2 size={15}/>{deleting?"Deleting…":"Delete project"}</button></div></div></div>}
  </main>;
}
