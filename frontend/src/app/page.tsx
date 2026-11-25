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
                <span className="text-xs font-semibold text-slate-200">Engineering flow</span>
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
                <p className="truncate text-sm font-semibold text-slate-800">AI engineering overview</p>
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
                  Your workspace at a glance
                </h1>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
                  AI-assisted drawing understanding, geometry intelligence and structured BOM workflows — monitored in one engineering workspace.
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Link
                  href="/projects"
                  className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50"
                >
                  <FolderKanban size={16} />
                  View projects
                </Link>
                <Link
                  href="/drawings"
                  className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-[0_6px_16px_rgba(37,99,235,0.2)] transition hover:bg-blue-700"
                >
                  <Plus size={17} />
                  Upload drawing
                  <ArrowUpRight size={14} className="opacity-70" />
                </Link>
              </div>
            </div>

<section className="ai-intelligence-panel relative overflow-hidden rounded-2xl border border-cyan-400/20 p-5 md:p-6" aria-label="AI CAD intelligence"><div className="ai-scan-line" /><div className="relative z-10 grid gap-5 lg:grid-cols-[1.2fr_.8fr] lg:items-center"><div><div className="mb-3 inline-flex items-center gap-2 rounded-full border border-cyan-300/25 bg-cyan-300/10 px-3 py-1.5 text-[10px] font-bold uppercase tracking-[.16em] text-cyan-200"><Sparkles size={13} className="animate-pulse" /> AI-powered CAD intelligence</div><h2 className="text-xl font-semibold text-white md:text-2xl">From raw geometry to engineering intelligence</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">AI-assisted drawing interpretation works alongside geometric analysis to turn complex DXF structures into traceable engineering data.</p><div className="mt-4 flex flex-wrap gap-2 text-[11px]"><span className="rounded-lg border border-white/10 bg-white/[.04] px-2.5 py-1.5 text-slate-300">Entity recognition</span><span className="rounded-lg border border-white/10 bg-white/[.04] px-2.5 py-1.5 text-slate-300">Geometry intelligence</span><span className="rounded-lg border border-white/10 bg-white/[.04] px-2.5 py-1.5 text-slate-300">BOM structuring</span></div></div><div className="ai-visual relative mx-auto flex min-h-36 w-full max-w-[360px] items-center justify-around"><div className="ai-orbit absolute left-1/2 top-1/2 h-40 w-40 -translate-x-1/2 -translate-y-1/2 rounded-full border border-cyan-300/15" /><div className="ai-orbit ai-orbit-delayed absolute left-1/2 top-1/2 h-52 w-52 -translate-x-1/2 -translate-y-1/2 rounded-full border border-blue-300/10" /><span className="relative z-10 rounded-2xl border border-blue-300/20 bg-blue-400/10 p-4 text-blue-200"><ScanLine size={24}/></span><span className="relative z-10 rounded-2xl border border-cyan-300/30 bg-cyan-300/10 p-5 text-cyan-200 shadow-[0_0_32px_rgba(34,211,238,.16)]"><BrainCircuit size={30} className="ai-brain-pulse"/></span><span className="relative z-10 rounded-2xl border border-violet-300/20 bg-violet-400/10 p-4 text-violet-200"><Boxes size={24}/></span><div className="absolute bottom-0 flex items-center gap-2 text-[10px] text-cyan-100/70"><Cpu size={12}/> AI analysis · Geometry · BOM</div></div></div><div className="relative z-10 mt-5 grid gap-2 border-t border-white/[.08] pt-4 sm:grid-cols-3"><div className="flex items-center gap-2 text-xs text-slate-300"><ShieldCheck size={14} className="text-emerald-300"/> Traceable engineering data</div><div className="flex items-center gap-2 text-xs text-slate-300"><ScanLine size={14} className="text-cyan-300"/> Drawing-aware analysis</div><div className="flex items-center gap-2 text-xs text-slate-300"><Sparkles size={14} className="text-violet-300"/> AI-assisted classification</div></div></section>

                        <div className="workflow-banner overflow-hidden rounded-2xl border border-[#1c3557] bg-[#14243a] shadow-[0_12px_32px_rgba(15,35,62,0.10)]">
              <div className="flex flex-col gap-4 px-5 py-4 sm:flex-row sm:items-center sm:justify-between md:px-6">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-blue-300/15 bg-blue-400/10 text-blue-200">
                    <Activity size={17} />
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-white">Drawing-to-BOM workflow</p>
                    <p className="mt-0.5 text-[10px] text-slate-400">A connected view of your engineering process</p>
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
