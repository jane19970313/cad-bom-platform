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

<section className="grating-intelligence-panel relative overflow-hidden rounded-2xl border p-5 md:p-6" aria-label="Steel grating drawing to bill of materials">
              <div className="grating-panel-glow" />
              <div className="relative z-10 grid gap-6 xl:grid-cols-[.78fr_1.22fr] xl:items-center">
                <div>
                  <div className="mb-3 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[.2em] text-cyan-300">
                    <span className="h-px w-6 bg-cyan-300" /> CAD intelligence
                  </div>
                  <h2 className="text-xl font-semibold tracking-tight text-white md:text-2xl">Steel grating · Drawing to BOM</h2>
                  <p className="mt-2 max-w-md text-sm leading-6 text-slate-400">Geometric recognition, member extraction and structured quantity takeoff.</p>
                  <div className="mt-5 flex flex-wrap gap-2">
                    <span className="technical-chip"><ScanLine size={12}/> DXF geometry</span>
                    <span className="technical-chip"><BrainCircuit size={12}/> AI classification</span>
                    <span className="technical-chip"><Boxes size={12}/> BOM structure</span>
                  </div>
                </div>
                <div className="grating-conversion-visual">
                  <div className="grating-drawing">
                    <div className="visual-label"><span>01 / GEOMETRY</span><span>DXF · TOP VIEW</span></div>
                    <svg viewBox="0 0 520 230" role="img" aria-label="Steel grating panel with bearing bars and cross bars">
                      <defs>
                        <linearGradient id="gratingSteel" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#8edcf0" stopOpacity=".9"/><stop offset="1" stopColor="#3d86b7" stopOpacity=".42"/></linearGradient>
                        <pattern id="gratingGrid" width="28" height="22" patternUnits="userSpaceOnUse"><path d="M0 0V22 M0 0H28" stroke="#7dd3fc" strokeOpacity=".13" strokeWidth="1"/></pattern>
                      </defs>
                      <rect x="26" y="20" width="468" height="188" rx="5" fill="url(#gratingGrid)" stroke="#6abbd8" strokeOpacity=".42"/>
                      {Array.from({length:13},(_,i)=><line key={"b"+i} x1={42+i*36} y1="31" x2={42+i*36} y2="197" stroke="url(#gratingSteel)" strokeWidth="5"/>)}
                      {Array.from({length:8},(_,i)=><line key={"c"+i} x1="34" y1={42+i*22} x2="486" y2={42+i*22} stroke="#8be2ef" strokeOpacity=".58" strokeWidth="2.2"/>)}
                      <path d="M26 14V7H494V14 M18 20H11V208H18 M502 20H509V208H502" fill="none" stroke="#67e8f9" strokeOpacity=".65"/>
                      <path d="M42 218H478 M42 214V222 M478 214V222" stroke="#8baecb" strokeOpacity=".65"/>
                      <text x="260" y="229" fill="#9ab8d1" fontSize="9" textAnchor="middle">BEARING BAR PITCH / CROSS BAR SPACING</text>
                      <circle cx="186" cy="86" r="17" fill="none" stroke="#fbbf24" strokeWidth="1.5" strokeDasharray="3 3"/>
                      <path d="M201 75L235 48H280" stroke="#fbbf24" strokeWidth="1" fill="none"/>
                      <text x="285" y="51" fill="#fcd34d" fontSize="10">BAR INTERSECTION</text>
                    </svg>
                  </div>
                  <div className="conversion-link"><span/><ArrowUpRight size={15}/><span/></div>
                  <div className="grating-bom">
                    <div className="visual-label"><span>02 / BOM</span><span>STRUCTURED OUTPUT</span></div>
                    <div className="bom-mini-head"><span>MEMBER</span><span>SPEC.</span><span>QTY</span></div>
                    <div className="bom-mini-row"><span><i className="bom-dot cyan"/>Bearing bar</span><span>FB 30×3</span><b>24</b></div>
                    <div className="bom-mini-row"><span><i className="bom-dot blue"/>Cross bar</span><span>Ø 6</span><b>18</b></div>
                    <div className="bom-mini-row"><span><i className="bom-dot violet"/>End band</span><span>FB 30×5</span><b>2</b></div>
                    <div className="bom-mini-foot"><CheckCircle2 size={12}/> Geometry-linked structure</div>
                  </div>
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
