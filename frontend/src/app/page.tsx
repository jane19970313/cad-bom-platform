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
  CheckCircle2,
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

          <div className="mt-auto">
            <div className="mb-4 rounded-2xl border border-white/[0.07] bg-white/[0.035] p-4">
              <div className="mb-3 flex items-center gap-2">
                <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-400/10 text-blue-300">
                  <Activity size={15} />
                </span>
                <span className="text-xs font-semibold text-slate-200">Process flow</span>
              </div>
              <div className="space-y-2.5">
                {["DXF intake", "Geometry analysis", "BOM generation"].map((step, index) => (
                  <div key={step} className="flex items-center gap-2.5">
                    <span className="flex h-5 w-5 items-center justify-center rounded-md border border-white/10 text-[10px] font-semibold text-slate-400">
                      0{index + 1}
                    </span>
                    <span className="text-xs text-slate-400">{step}</span>
                  </div>
                ))}
              </div>
              <p className="mt-3 border-t border-white/[0.07] pt-3 text-[10px] leading-4 text-slate-500">
                From drawing data to structured engineering output.
              </p>
            </div>
            <div className="flex items-center gap-2 px-3 text-[10px] text-slate-600">
              <Boxes size={13} />
              <span>CAD2BOM · Engineering tools</span>
            </div>
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
                <Link
                  href="/drawings"
                  className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-[0_6px_16px_rgba(37,99,235,0.2)] transition hover:bg-blue-700"
                >
                  <Plus size={17} />
                  Import DXF
                  <ArrowUpRight size={14} className="opacity-70" />
                </Link>
              </div>
            </div>

<section className="grating-intelligence-panel relative overflow-hidden rounded-2xl border p-5 md:p-6" aria-label="AI steel grating 3D analysis and BOM generation">
              <div className="grating-panel-glow" />
              <div className="relative z-10 grid gap-5 xl:grid-cols-[.65fr_1.35fr] xl:items-center">
                <div className="relative z-10">
                  <div className="mb-3 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[.2em] text-cyan-300">
                    <span className="h-px w-6 bg-cyan-300" /> AI · CAD · BOM
                  </div>
                  <h2 className="text-xl font-semibold tracking-tight text-white md:text-2xl">3D Geometry Intelligence</h2>
                  <p className="mt-2 max-w-xs text-sm leading-6 text-slate-400">Steel grating recognition and automated bill of materials.</p>
                  <div className="mt-5 flex flex-wrap gap-2">
                    <span className="technical-chip"><BrainCircuit size={12}/> AI ANALYSIS</span>
                    <span className="technical-chip"><Boxes size={12}/> BOM OUTPUT</span>
                  </div>
                </div>
                <div className="grating-3d-scene">
                  <div className="scene-caption scene-caption-left">3D STRUCTURAL MODEL <span>DXF</span></div>
                  <svg className="grating-3d-model" viewBox="0 0 620 300" role="img" aria-label="Isometric three-dimensional steel grating structure being analyzed by AI and converted to a bill of materials">
                    <defs>
                      <linearGradient id="steelTop" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#a5f3fc" stopOpacity=".88"/><stop offset=".55" stopColor="#38bdf8" stopOpacity=".62"/><stop offset="1" stopColor="#2563a6" stopOpacity=".45"/></linearGradient>
                      <linearGradient id="steelSide" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#3287b4" stopOpacity=".65"/><stop offset="1" stopColor="#102b48" stopOpacity=".95"/></linearGradient>
                      <radialGradient id="aiCore"><stop offset="0" stopColor="#67e8f9" stopOpacity=".34"/><stop offset="1" stopColor="#67e8f9" stopOpacity="0"/></radialGradient>
                      <filter id="steelGlow"><feGaussianBlur stdDeviation="3" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
                    </defs>
                    <ellipse cx="300" cy="245" rx="238" ry="30" fill="#020817" opacity=".45"/>
                    <g className="grating-model-float">
                      <polygon points="75,105 330,25 535,112 276,198" fill="#143a59" fillOpacity=".55" stroke="#75dff2" strokeOpacity=".7" strokeWidth="1.5"/>
                      <polygon points="75,105 276,198 276,225 75,132" fill="url(#steelSide)" stroke="#4b9fc2" strokeOpacity=".55"/>
                      <polygon points="276,198 535,112 535,139 276,225" fill="#12314e" stroke="#4b9fc2" strokeOpacity=".55"/>
                      <g stroke="url(#steelTop)" strokeWidth="7" strokeLinecap="round" filter="url(#steelGlow)">
                        {#each Array.from({length:13},(_,i)=>i) as i}<line x1={88+i*19.8} y1={110-i*6.2} x2={289+i*19.8} y2={202-i*6.2}/>{/each}
                      </g>
                      <g stroke="#8be7f4" strokeOpacity=".78" strokeWidth="3.2">
                        {#each Array.from({length:9},(_,i)=>i) as i}<line x1={85+i*24.8} y1={101+i*11.4} x2={338+i*24.8} y2={22+i*11.4}/>{/each}
                      </g>
                      <g fill="none" stroke="#c4f6ff" strokeOpacity=".55" strokeWidth="1">
                        <polygon points="75,105 330,25 535,112 276,198"/>
                        <path d="M75 105L75 132L276 225L535 139L535 112"/>
                      </g>
                    </g>
                    <g className="ai-analysis-orbit" transform="translate(307 128)">
                      <circle r="67" fill="url(#aiCore)"/>
                      <circle r="43" fill="none" stroke="#67e8f9" strokeOpacity=".32" strokeDasharray="3 6"/>
                      <circle r="29" fill="#0d263b" fillOpacity=".86" stroke="#67e8f9" strokeOpacity=".72"/>
                      <path d="M-15 -5L0 -18L15 -5L0 9Z M-15 -5V10L0 23L15 10V-5 M0 9V23" fill="none" stroke="#a5f3fc" strokeWidth="1.6"/>
                      <circle r="3" fill="#d9fbff" filter="url(#steelGlow)"/>
                    </g>
                    <path d="M353 128H438" stroke="#67e8f9" strokeOpacity=".55" strokeWidth="1.5" strokeDasharray="4 5"/>
                    <path d="M431 122L440 128L431 134" fill="none" stroke="#67e8f9" strokeWidth="1.5"/>
                    <g transform="translate(452 72)">
                      <rect x="0" y="0" width="130" height="126" rx="10" fill="#0b1b2d" fillOpacity=".94" stroke="#68c9dc" strokeOpacity=".4"/>
                      <text x="13" y="19" fill="#7dd3fc" fontSize="9" letterSpacing="1.5">BOM OUTPUT</text>
                      <g transform="translate(13 32)">
                        <path d="M0 0H103 M0 25H103 M0 50H103 M0 75H103" stroke="#42627d" strokeOpacity=".55"/>
                        <path d="M0 0H8V8H0Z M0 25H8V33H0Z M0 50H8V58H0Z M0 75H8V83H0Z" fill="#67e8f9" fillOpacity=".8"/>
                        <path d="M16 4H72 M16 29H88 M16 54H65 M16 79H80" stroke="#b7d1e3" strokeOpacity=".75" strokeWidth="3" strokeLinecap="round"/>
                        <path d="M91 4H103 M91 29H103 M91 54H103 M91 79H103" stroke="#38bdf8" strokeWidth="3" strokeLinecap="round"/>
                      </g>
                    </g>
                    <text x="77" y="270" fill="#7f9db8" fontSize="9" letterSpacing="1.4">STRUCTURAL GEOMETRY</text>
                    <text x="452" y="216" fill="#67e8f9" fontSize="9" letterSpacing="1.3">INTELLIGENT TAKEOFF</text>
                  </svg>
                  <div className="scene-caption scene-caption-bottom"><span>GEOMETRY</span><i/><span>AI INFERENCE</span><i/><span>BOM</span></div>
                </div>
              </div>
            </section>

                        <div className="workflow-banner overflow-hidden rounded-2xl border border-[#1c3557] bg-[#14243a] shadow-[0_12px_32px_rgba(15,35,62,0.10)]">
              <div className="flex flex-col gap-4 px-5 py-4 sm:flex-row sm:items-center sm:justify-between md:px-6">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-blue-300/15 bg-blue-400/10 text-blue-200">
                    <Activity size={17} />
                  </div>
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[.12em] text-white">Process sequence</p>
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.12em]">
                  {["DXF upload", "Extraction", "Geometry", "BOM"].map((stage, index) => (
                    <div key={stage} className="flex items-center gap-2">
                      <span className={`rounded-lg border px-2.5 py-1.5 ${
                        index === 0
                          ? "border-blue-300/30 bg-blue-400/15 text-blue-200"
                          : "border-white/10 bg-white/[0.04] text-slate-400"
                      }`}>
                        {stage}
                      </span>
                      {index < 3 && <span className="text-slate-600">›</span>}
                    </div>
                  ))}
                </div>
              </div>
              <div className="h-px bg-gradient-to-r from-blue-400/50 via-slate-500/20 to-transparent" />
            </div>

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
