import Link from "next/link";
import {
  Activity,
  BrainCircuit,
  Cpu,
  ScanLine,
  Sparkles,
  ShieldCheck,
  ArrowUpRight,
  Boxes,
  FileCode2,
  FolderKanban,
  LayoutDashboard,
  Layers3,
  Plus,
  Workflow,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import UserMenu from "@/components/dashboard/user-menu";
import DashboardData from "@/components/dashboard/dashboard-data";

const navigation: {
  label: string;
  href: string;
  icon: LucideIcon;
}[] = [
  { label: "Overview", href: "/", icon: LayoutDashboard },
  { label: "Projects", href: "/projects", icon: FolderKanban },
  { label: "Drawings", href: "/drawings", icon: FileCode2 },
  { label: "Processing jobs", href: "/pipeline", icon: Workflow },
];

function SidebarLink({
  icon: Icon,
  label,
  href,
  active = false,
}: {
  icon: LucideIcon;
  label: string;
  href: string;
  active?: boolean;
}) {
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={`group flex items-center gap-3 rounded-xl px-3.5 py-3 text-sm transition-all duration-200 ${
        active
          ? "bg-blue-500/15 text-white ring-1 ring-inset ring-blue-400/20"
          : "text-slate-400 hover:bg-white/[0.06] hover:text-slate-100"
      }`}
    >
      <Icon
        size={18}
        strokeWidth={active ? 2.2 : 1.8}
        className={active ? "text-blue-300" : "text-slate-500 group-hover:text-slate-300"}
      />
      <span className="flex-1">{label}</span>
      {active && <span className="h-1.5 w-1.5 rounded-full bg-blue-300 shadow-[0_0_10px_rgba(147,197,253,0.9)]" />}
    </Link>
  );
}

export default function DashboardPage() {
  return (
    <main className="engineering-dashboard min-h-screen bg-[#0b1220] text-slate-100">
      <div className="flex min-h-screen">
        <aside className="hidden w-[264px] shrink-0 flex-col border-r border-white/[0.06] bg-[#080f1d] px-4 py-6 text-white lg:flex">
          <Link href="/" className="mb-10 flex items-center gap-3 px-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-blue-300/20 bg-blue-400/10 text-blue-300 shadow-[0_0_24px_rgba(59,130,246,0.12)]">
              <Layers3 size={21} />
            </div>
            <div>
              <p className="text-[15px] font-bold tracking-[0.08em] text-white">CAD2BOM</p>
              <p className="mt-0.5 text-[10px] font-medium uppercase tracking-[0.18em] text-slate-500">Engineering workspace</p>
            </div>
          </Link>

          <div className="mb-3 px-3 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">
            Workspace
          </div>
          <nav aria-label="Main navigation" className="space-y-1.5">
            {navigation.map((item, index) => (
              <SidebarLink
                key={item.href}
                {...item}
                active={index === 0}
              />
            ))}
          </nav>

          <div className="mt-auto px-3 text-[10px] text-slate-600">
            <div className="flex items-center gap-2"><Boxes size={13}/><span>CAD2BOM · Engineering tools</span></div>
          </div>
        </aside>

        <section className="min-w-0 flex-1">
          <header className="sticky top-0 z-20 flex h-[68px] items-center justify-between border-b border-white/[0.07] bg-[#0d1727]/90 px-5 backdrop-blur-xl md:px-8">
            <div className="flex min-w-0 items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-100 text-slate-600 lg:hidden">
                <Layers3 size={18} />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2 text-xs text-slate-400">
                  <span className="hidden sm:inline">CAD2BOM</span>
                  <span className="hidden sm:inline text-slate-300">/</span>
                  <span className="font-medium text-slate-600">Workspace</span>
                </div>
                <p className="truncate text-sm font-semibold text-slate-100">CAD intelligence</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className="hidden items-center gap-2 rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1.5 text-[11px] font-semibold text-emerald-300 md:inline-flex">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                Workspace ready
              </span>
              <UserMenu />
            </div>
          </header>

          <div className="mx-auto max-w-[1480px] space-y-7 p-5 md:p-8">
            <div className="flex flex-col justify-between gap-5 xl:flex-row xl:items-end">
              <div>
                <div className="mb-3 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-cyan-300">
                  <span className="h-px w-6 bg-blue-500" />
                  Engineering intelligence
                </div>
                <h1 className="text-2xl font-bold tracking-tight text-slate-50 md:text-[30px]">
                  Engineering overview
                </h1>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
                  Steel grating geometry · AI classification · Structured BOM
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Link
                  href="/projects"
                  className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.045] px-4 py-2.5 text-sm font-semibold text-slate-200 transition hover:border-cyan-300/30 hover:bg-white/[0.08]"
                >
                  <FolderKanban size={16} />
                  Projects
                </Link>

              </div>
            </div>

<section className="grating-intelligence-panel relative overflow-hidden rounded-2xl border" aria-label="AI-powered CAD to BOM engineering visualization">
              <div className="hud-background-structure" aria-hidden="true"/>
              <div className="hud-scan-sweep" aria-hidden="true"/>
              <div className="relative z-10 p-5 md:p-7 xl:p-8">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-cyan-200/10 pb-4">
                  <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[.22em] text-cyan-200">
                    <span className="hud-live-dot"/>
                    AI ENGINEERING SYSTEM <span className="text-slate-600">/</span> CAD INTERPRETATION
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <span className="hud-status-chip"><BrainCircuit size={12}/> NEURAL GEOMETRY ANALYSIS</span>
                    <span className="hud-status-chip hud-status-chip-active"><span className="hud-live-dot"/> SYSTEM ONLINE</span>
                  </div>
                </div>

                <div className="grid gap-5 pt-6 xl:grid-cols-[.72fr_1.28fr] xl:items-end">
                  <div className="max-w-xl">
                    <p className="mb-3 text-[10px] font-bold uppercase tracking-[.28em] text-cyan-300">FROM 2D DRAWING TO INTELLIGENT BOM</p>
                    <h2 className="hud-hero-title text-[clamp(1.8rem,3.15vw,3.15rem)] font-black leading-[1.02] tracking-[-.05em] text-white">
                      AI-Powered<br/><span className="hud-title-equation"><span>CAD</span><i className="hud-title-arrow">→</i><span>BOM</span></span>
                    </h2>
                    <p className="mt-4 max-w-md text-sm leading-6 text-slate-300/80 md:text-[15px]">
                      AI understands every line, profile and connection in your 2D steel drawings — then transforms them into a structured bill of materials.
                    </p>
                    <div className="mt-5 flex flex-wrap gap-2">
                      <span className="hud-feature-chip"><ScanLine size={13}/> 2D DRAWING RECOGNITION</span>
                      <span className="hud-feature-chip"><BrainCircuit size={13}/> AI STRUCTURAL ANALYSIS</span>
                      <span className="hud-feature-chip"><Boxes size={13}/> AUTOMATED TAKEOFF</span>
                    </div>
                    <div className="mt-6 flex items-center gap-3">
                      <Link href="/drawings" className="hud-primary-action"><Plus size={16}/> Import CAD drawing <ArrowUpRight size={14}/></Link>
                      <span className="text-[10px] font-mono tracking-wider text-cyan-100/45">DXF / DWG WORKFLOW</span>
                    </div>
                  </div>

                  <div className="hud-visual-stage">
                    <div className="hud-stage-grid" aria-hidden="true"/>
                    <div className="hud-stage-corner hud-stage-corner-tl"/>
                    <div className="hud-stage-corner hud-stage-corner-tr"/>
                    <div className="hud-stage-corner hud-stage-corner-bl"/>
                    <div className="hud-stage-corner hud-stage-corner-br"/>
                    <div className="hud-stage-label hud-stage-label-left"><span>01</span> 2D CAD INPUT</div>
                    <div className="hud-stage-label hud-stage-label-center"><span>02</span> AI STRUCTURAL RECOGNITION</div>
                    <div className="hud-stage-label hud-stage-label-right"><span>03</span> BOM OUTPUT</div>

                    <div className="hud-cad-preview">
                      <div className="hud-panel-topline"><FileCode2 size={11}/> DXF / PLAN VIEW <span>2D</span></div>
                      <div className="hud-blueprint-drawing">
                        <svg viewBox="0 0 150 112" role="img" aria-label="Simplified two-dimensional steel grating CAD plan">
                          <g fill="none" stroke="#79e8fa" strokeWidth="1.1" opacity=".9">
                            <path d="M12 28L75 8L138 31L75 53Z M12 28V82L75 105L138 82V31"/>
                            {Array.from({length:7},(_,i)=><path key={`cad-v-${i}`} d={`M${20+i*8.8} ${31+i*2.9}L${83+i*8.8} ${54+i*2.9}`}/>)}
                            {Array.from({length:6},(_,i)=><path key={`cad-h-${i}`} d={`M${17+i*2.5} ${40+i*8.5}L${80+i*2.5} ${18+i*8.5}`}/>)}
                          </g>
                          <g fill="none" stroke="#3989b2" strokeWidth=".65" strokeDasharray="2 3">
                            <path d="M5 20L75 0L145 25 M5 88L75 112L145 88"/>
                          </g>
                        </svg>
                      </div>
                      <div className="hud-panel-foot"><span>PLAN / SECTION</span><span>DXF</span></div>
                    </div>

                    <div className="hud-ai-core" aria-hidden="true">
                      <div className="hud-ai-ring hud-ai-ring-outer"/>
                      <div className="hud-ai-ring hud-ai-ring-inner"/>
                      <div className="hud-ai-core-center"><BrainCircuit size={25}/></div>
                      <span className="hud-ai-core-caption">AI CORE</span>
                    </div>

                    <div className="hud-steel-model" role="img" aria-label="High-detail isometric steel grating platform supported by structural H-beams">
                      <svg className="hud-grating-vector" viewBox="0 0 560 360" aria-hidden="true">
                        <defs>
                          <linearGradient id="steelTop" x1="0" y1="0" x2="1" y2="1"><stop stopColor="#dce8ef"/><stop offset=".34" stopColor="#7893a8"/><stop offset=".7" stopColor="#405c72"/><stop offset="1" stopColor="#b9cbd5"/></linearGradient>
                          <linearGradient id="steelSide" x1="0" y1="0" x2="0" y2="1"><stop stopColor="#8ca7b8"/><stop offset="1" stopColor="#263c50"/></linearGradient>
                          <linearGradient id="beamMetal" x1="0" y1="0" x2="1" y2="1"><stop stopColor="#d4e1e8"/><stop offset=".45" stopColor="#637f94"/><stop offset="1" stopColor="#263e52"/></linearGradient>
                          <filter id="steelShadow" x="-30%" y="-30%" width="160%" height="180%"><feGaussianBlur stdDeviation="8"/></filter>
                        </defs>
                        <ellipse cx="286" cy="293" rx="222" ry="25" fill="#000" opacity=".45" filter="url(#steelShadow)"/>
                        <g opacity=".98">
                          <path d="M67 139L283 55L504 137L286 229Z" fill="url(#steelTop)" stroke="#d5e8f1" strokeWidth="1.4"/>
                          <path d="M67 139L286 229V251L67 160Z" fill="url(#steelSide)" stroke="#7898ac"/>
                          <path d="M286 229L504 137V159L286 251Z" fill="#314b60" stroke="#7898ac"/>
                          {Array.from({length:19},(_,i)=><path key={`bar-long-${i}`} d={`M${79+i*11.2} ${143-i*4.3}L${297+i*11.2} ${235-i*4.3}`} stroke={i%2===0?"#dbe8ee":"#526f84"} strokeWidth="3.5" opacity=".95"/>)}
                          {Array.from({length:13},(_,i)=><path key={`bar-cross-${i}`} d={`M${82+i*16.7} ${133-i*6.45}L${299+i*16.7} ${223-i*6.45}`} stroke="#d2e1e9" strokeWidth="2.4" opacity=".8" transform="rotate(-21 286 150)"/>)}
                          <path d="M67 139L283 55L504 137L286 229Z" fill="none" stroke="#e5f3fa" strokeWidth="2.5" opacity=".9"/>
                        </g>
                        <g transform="translate(0 5)">
                          <path d="M91 164L111 172L111 260L91 252Z M91 164L111 172L133 163L113 155Z" fill="url(#beamMetal)" stroke="#b5c9d4"/>
                          <path d="M111 172L133 163L133 250L111 260Z" fill="#314b60" stroke="#8da9ba"/>
                          <path d="M410 155L431 147L431 235L410 244Z M410 155L431 147L454 156L433 165Z" fill="url(#beamMetal)" stroke="#b5c9d4"/>
                          <path d="M431 147L454 156L454 244L431 235Z" fill="#314b60" stroke="#8da9ba"/>
                          <path d="M74 250L285 337L493 250L472 242L285 319L95 242Z" fill="url(#beamMetal)" stroke="#9bb4c2" strokeWidth="1.5"/>
                        </g>
                        <g transform="translate(384 270) scale(.72)">
                          <path d="M0 0H120V17H70V95H50V17H0Z" fill="url(#beamMetal)" stroke="#d6e6ed" strokeWidth="2"/>
                          <path d="M50 17H70V95H50Z" fill="#2a4358"/>
                          <path d="M0 0H120V7H0Z" fill="#e4eef3" opacity=".7"/>
                        </g>
                      </svg>
                      <div className="hud-model-scanline"/>
                      <div className="hud-model-tag"><span className="hud-live-dot"/> 3D STEEL GRATING ASSEMBLY</div>
                    </div>

                    <div className="hud-bom-preview">
                      <div className="hud-panel-topline"><Boxes size={11}/> BOM OUTPUT · SAMPLE <span>XLSX</span></div>
                      <div className="hud-bom-table-wrap">
                        <table className="hud-bom-table">
                          <thead><tr><th>MARK</th><th>DESCRIPTION</th><th>QTY</th></tr></thead>
                          <tbody>
                            <tr className="bom-row bom-row-cyan"><td><span className="bom-mark">GB-01</span></td><td>Grating panel</td><td><span className="bom-qty">08</span></td></tr>
                            <tr className="bom-row bom-row-amber"><td><span className="bom-mark">FB-04</span></td><td>Flat bar 40×5</td><td><span className="bom-qty">24</span></td></tr>
                            <tr className="bom-row bom-row-violet"><td><span className="bom-mark">HB-02</span></td><td>H-beam 200</td><td><span className="bom-qty">04</span></td></tr>
                            <tr className="bom-row bom-row-emerald"><td><span className="bom-mark">CL-08</span></td><td>Clip / fastener</td><td><span className="bom-qty">32</span></td></tr>
                          </tbody>
                          <tfoot><tr><td colSpan={2}>TOTAL ITEMS</td><td><span className="bom-total">68</span></td></tr></tfoot>
                        </table>
                      </div>
                      <div className="hud-panel-foot"><span>ILLUSTRATIVE MATERIAL TAKEOFF</span><span>PREVIEW</span></div>
                    </div>

                    <div className="hud-data-stream hud-data-stream-one"/>
                    <div className="hud-data-stream hud-data-stream-two"/>
                    <div className="hud-stage-bottomline"><span>GEOMETRY EXTRACTION</span><i/><span>AI CLASSIFICATION</span><i/><span>STRUCTURED OUTPUT</span></div>
                  </div>
                </div>
              </div>
            </section>



            <DashboardData />

            <footer className="flex flex-col gap-2 border-t border-white/[0.08] pt-5 text-[11px] text-slate-500 sm:flex-row sm:items-center sm:justify-between">
              <span>CAD2BOM Engineering Workspace</span>
              <span>Drawing intelligence · Geometry analysis · Bill of materials</span>
            </footer>
          </div>
        </section>
      </div>
    </main>
  );
}
