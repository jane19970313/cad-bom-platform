"use client";

import { useCallback,useEffect,useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowUpRight,CheckCircle2,FileCode2,FileUp,FolderKanban,Loader2,Play,RefreshCw,Trash2,UploadCloud } from "lucide-react";
import { drawingsApi,processingApi,projectsApi } from "@/lib/api";
import type { Project } from "@/types/project";
import type { Drawing } from "@/types/drawing";

function formatSize(bytes:number){if(bytes<1024)return `${bytes} B`;if(bytes<1048576)return `${(bytes/1024).toFixed(1)} KB`;return `${(bytes/1048576).toFixed(2)} MB`;}
function formatDate(value:string){return new Date(value).toLocaleString();}

export default function DrawingsPage(){
 const router=useRouter();
 const [projects,setProjects]=useState<Project[]>([]);
 const [projectId,setProjectId]=useState("");
 const [drawings,setDrawings]=useState<Drawing[]>([]);
 const [file,setFile]=useState<File|null>(null);
 const [loading,setLoading]=useState(true);
 const [loadingDrawings,setLoadingDrawings]=useState(false);
 const [uploading,setUploading]=useState(false);
 const [processingId,setProcessingId]=useState<string|null>(null);
 const [deleting,setDeleting]=useState<string|null>(null);
 const [confirmDelete,setConfirmDelete]=useState<Drawing|null>(null);
 const [error,setError]=useState("");
 const [success,setSuccess]=useState("");
 const selectedProject=projects.find(p=>p.id===projectId);

 const loadDrawings=useCallback(async(id:string)=>{
  if(!id){setDrawings([]);return;}
  setLoadingDrawings(true);setError("");
  try{const result=await drawingsApi.getProjectDrawings(id);setDrawings(result.items);}
  catch(e){setError(e instanceof Error?e.message:"Unable to load drawings.");}
  finally{setLoadingDrawings(false);}
 },[]);
 useEffect(()=>{let active=true;(async()=>{try{const list=await projectsApi.getProjects();if(!active)return;setProjects(list);const requested=new URLSearchParams(window.location.search).get("projectId");setProjectId(list.find(p=>p.id===requested)?.id??list[0]?.id??"");}catch(e){if(active)setError(e instanceof Error?e.message:"Unable to load projects.");}finally{if(active)setLoading(false);}})();return()=>{active=false;};},[]);
 useEffect(()=>{void loadDrawings(projectId);},[projectId,loadDrawings]);

 async function upload(event:React.FormEvent<HTMLFormElement>){
  event.preventDefault();if(!projectId||!file)return;
  if(!file.name.toLowerCase().endsWith(".dxf")){setError("Only DXF files can be uploaded.");return;}
  setUploading(true);setError("");setSuccess("");
  try{const item=await drawingsApi.uploadDrawing(projectId,file);setDrawings(v=>[item,...v]);setFile(null);const input=document.getElementById("drawing-file") as HTMLInputElement|null;if(input)input.value="";setSuccess(`${item.original_filename} uploaded successfully.`);}
  catch(e){setError(e instanceof Error?e.message:"DXF upload failed.");}
  finally{setUploading(false);}
 }
 async function process(drawing:Drawing){
  setProcessingId(drawing.id);setError("");setSuccess("");
  try{const job=await processingApi.submitDrawingProcessing(drawing.id);if(!job.id)throw new Error("The processing service did not return a job ID.");router.push(`/pipeline?jobId=${encodeURIComponent(job.id)}`);}
  catch(e){setError(e instanceof Error?e.message:"Unable to start processing.");}
  finally{setProcessingId(null);}
 }
 async function remove(drawing:Drawing){
  setDeleting(drawing.id);setError("");setSuccess("");
  try{await drawingsApi.deleteDrawing(drawing.id);setDrawings(v=>v.filter(d=>d.id!==drawing.id));setConfirmDelete(null);setSuccess(`${drawing.original_filename} was deleted.`);}
  catch(e){setError(e instanceof Error?e.message:"Unable to delete drawing.");}
  finally{setDeleting(null);}
 }
 return <main className="workspace-page min-h-screen"><div className="workspace-page-inner">
  <div className="workspace-breadcrumb"><Link href="/projects">Projects</Link><span>/</span><span>Drawings</span></div>
  <header className="workspace-page-header"><div><div className="workspace-eyebrow"><FileCode2 size={14}/> CAD INPUT MANAGEMENT</div><h1>DXF Drawings</h1><p>Upload, organize and run AI-powered drawing analysis.</p></div><button className="hud-button hud-button-secondary" onClick={()=>void loadDrawings(projectId)} disabled={!projectId||loadingDrawings}><RefreshCw size={15} className={loadingDrawings?"animate-spin":""}/> Refresh</button></header>
  <div className="workspace-stat-strip"><div><span>ACTIVE PROJECT</span><strong className="stat-project-name">{selectedProject?.name??(loading?"Loading…":"—")}</strong></div><div><span>DRAWINGS</span><strong>{drawings.length}</strong></div><div><span>INPUT FORMAT</span><strong>DXF / 2D CAD</strong></div></div>
  {error&&<div className="workspace-alert workspace-alert-error">{error}</div>}{success&&<div className="workspace-alert workspace-alert-success"><CheckCircle2 size={15}/>{success}</div>}
  <div className="drawing-workspace-grid">
   <section className="workspace-panel drawing-upload-panel"><div className="workspace-section-heading"><div><span className="workspace-kicker">INGESTION</span><h2>Upload drawing</h2><p>Bring a DXF file into your project workspace.</p></div><span className="workspace-icon-tile"><UploadCloud size={19}/></span></div>
    {loading?<div className="workspace-empty">Loading projects…</div>:projects.length===0?<div className="workspace-empty"><FolderKanban size={28}/><h3>No project available</h3><p>Create a project before uploading drawings.</p><Link href="/projects" className="project-open-link">Create project <ArrowUpRight size={15}/></Link></div>:<>
     <label className="workspace-field-label">TARGET PROJECT<select value={projectId} onChange={e=>{setProjectId(e.target.value);setSuccess("");}}>{projects.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
     <form onSubmit={upload}><label htmlFor="drawing-file" className={`drawing-dropzone ${file?"has-file":""}`}><span className="drawing-upload-icon"><FileUp size={25}/></span><strong>{file?file.name:"Drop your DXF drawing here"}</strong><span>{file?`${formatSize(file.size)} · Ready to upload`:"or browse files from your computer"}</span><em>DXF FILES ONLY</em><input id="drawing-file" type="file" accept=".dxf,application/dxf,application/octet-stream" onChange={e=>setFile(e.target.files?.[0]??null)}/></label>
      <button type="submit" className="hud-button hud-button-primary drawing-upload-submit" disabled={!file||!projectId||uploading}>{uploading?<Loader2 size={16} className="animate-spin"/>:<FileUp size={16}/>} {uploading?"Uploading drawing…":"Upload to project"}</button>
     </form>
     <div className="drawing-upload-note"><span/>Files are validated before being stored in your project.</div>
    </>}
   </section>
   <section className="workspace-panel drawing-library-panel"><div className="workspace-section-heading"><div><span className="workspace-kicker">DRAWING LIBRARY</span><h2>Project drawings <span className="workspace-count">{drawings.length}</span></h2><p>{selectedProject?.name??"Select a project"} · Stored DXF source files</p></div></div>
    {loadingDrawings?<div className="workspace-empty">Loading drawing library…</div>:drawings.length===0?<div className="workspace-empty"><FileCode2 size={30}/><h3>No drawings in this project</h3><p>Upload a DXF file to start the analysis workflow.</p></div>:<div className="drawing-list">{drawings.map((d,index)=><article className="drawing-hud-row" key={d.id}><div className="drawing-file-icon"><FileCode2 size={20}/><span>DXF</span></div><div className="drawing-file-info"><div className="drawing-name-line"><h3 title={d.original_filename}>{d.original_filename}</h3><span className={`drawing-status status-${d.status.toLowerCase()}`}>{d.status}</span></div><p>{formatSize(d.file_size)} <i/> {d.mime_type} <i/> {formatDate(d.created_at)}</p><small>DRAWING · {String(index+1).padStart(3,"0")} · {d.id.slice(0,8).toUpperCase()}</small></div><div className="drawing-row-actions"><button className="hud-button hud-button-primary" onClick={()=>void process(d)} disabled={processingId!==null||deleting!==null}>{processingId===d.id?<Loader2 size={15} className="animate-spin"/>:<Play size={15}/>} {processingId===d.id?"Starting…":"Run AI analysis"}</button><button className="workspace-icon-button danger" title="Delete drawing" onClick={()=>setConfirmDelete(d)} disabled={processingId!==null||deleting!==null}><Trash2 size={16}/></button></div></article>)}</div>}
   </section>
  </div>
 </div>
 {confirmDelete&&<div className="workspace-modal-backdrop" role="presentation" onMouseDown={e=>{if(e.target===e.currentTarget)setConfirmDelete(null);}}><div className="workspace-confirm-modal" role="dialog" aria-modal="true" aria-labelledby="delete-drawing-title"><span className="workspace-danger-icon"><Trash2 size={20}/></span><h2 id="delete-drawing-title">Delete drawing?</h2><p>“{confirmDelete.original_filename}” will be permanently removed from storage and this project. This action cannot be undone.</p><div><button className="hud-button hud-button-secondary" onClick={()=>setConfirmDelete(null)} disabled={!!deleting}>Cancel</button><button className="hud-button hud-button-danger" onClick={()=>void remove(confirmDelete)} disabled={!!deleting}><Trash2 size={15}/>{deleting?"Deleting…":"Delete drawing"}</button></div></div></div>}
 </main>;
}
