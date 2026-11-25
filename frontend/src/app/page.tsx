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

<section className="grating-intelligence-panel relative overflow-hidden rounded-2xl border p-5 md:p-6" aria-label="AI-powered 2D CAD drawing analysis and steel grating bill of materials generation">
              <div className="grating-panel-glow" />
              <div className="relative z-10 grid gap-4 xl:grid-cols-[.62fr_1.38fr] xl:items-center">
                <div className="relative z-10">
                  <div className="mb-3 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[.2em] text-cyan-300">
                    <span className="h-px w-6 bg-cyan-300" /> AI-POWERED ENGINEERING
                  </div>
                  <h2 className="text-xl font-semibold tracking-tight text-white md:text-[27px]">AI-Powered CAD to BOM</h2>
                  <p className="mt-2 max-w-xs text-sm leading-6 text-slate-400">Upload 2D steel-grating drawings. AI reads the geometry and builds your bill of materials.</p>
                  <div className="mt-5 flex flex-wrap gap-2">
                    <span className="technical-chip"><BrainCircuit size={12}/> AI GEOMETRY RECOGNITION</span>
                    <span className="technical-chip"><Boxes size={12}/> AUTOMATED BOM</span>
                  </div>
                  <div className="mt-5 flex items-center gap-2 text-[10px] font-semibold tracking-[.12em] text-slate-500">
                    <span className="h-1.5 w-1.5 rounded-full bg-cyan-300 shadow-[0_0_9px_rgba(103,232,249,.8)]" />
                    2D DRAWING <span className="text-cyan-400/70">→</span> AI ANALYSIS <span className="text-cyan-400/70">→</span> BOM
                  </div>
                </div>
                <div className="grating-3d-scene">
                  <div className="scene-caption"><span>DRAWING-TO-BOM WORKFLOW</span><span className="scene-live"><i/> AI ENGINE ACTIVE</span></div>
                  <svg className="grating-3d-model" viewBox="0 0 900 360" role="img" aria-label="A 2D steel grating CAD drawing is interpreted by an AI engine, rendered as a realistic three-dimensional steel grating panel, and converted into a structured bill of materials preview">
                    <defs>
                      <linearGradient id="steelTop" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#e0f7ff"/><stop offset=".28" stopColor="#7dd3e8"/><stop offset=".7" stopColor="#3986ad"/><stop offset="1" stopColor="#1c4568"/></linearGradient>
                      <linearGradient id="steelSide" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#397b9e"/><stop offset=".35" stopColor="#17405e"/><stop offset="1" stopColor="#091a2c"/></linearGradient>
                      <linearGradient id="crossSteel" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#d8f7ff"/><stop offset=".45" stopColor="#63b9d5"/><stop offset="1" stopColor="#1d5275"/></linearGradient>
                      <linearGradient id="bomSurface" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#122b42"/><stop offset="1" stopColor="#091827"/></linearGradient>
                      <radialGradient id="aiCore"><stop offset="0" stopColor="#67e8f9" stopOpacity=".42"/><stop offset="1" stopColor="#67e8f9" stopOpacity="0"/></radialGradient>
                      <filter id="steelShadow" x="-30%" y="-30%" width="160%" height="180%"><feGaussianBlur in="SourceAlpha" stdDeviation="5"/><feOffset dy="8"/><feComponentTransfer><feFuncA type="linear" slope=".42"/></feComponentTransfer><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter>
                      <filter id="cyanGlow"><feGaussianBlur stdDeviation="3" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
                    </defs>

                    <ellipse cx="370" cy="286" rx="205" ry="24" fill="#020817" opacity=".52"/>

                    <g className="cad-input-card">
                      <rect x="8" y="112" width="128" height="120" rx="9" fill="#0a1a2b" stroke="#47728f" strokeOpacity=".65"/>
                      <path d="M20 130H124 M20 213H124" stroke="#42627d" strokeOpacity=".45"/>
                      <text x="20" y="126" fill="#8ca9c3" fontSize="8" letterSpacing="1.2">2D DXF INPUT</text>
                      <g transform="translate(27 148)" fill="none" stroke="#70d9ed" strokeWidth="1.1" opacity=".92">
                        <path d="M0 20L40 5L78 20L38 35Z M0 20V49L38 65L78 49V20"/>
                        <path d="M8 23L46 8 M16 27L54 12 M24 31L62 16 M32 34L70 19"/>
                        <path d="M10 14L10 43 M22 10L22 48 M34 7L34 54 M46 10L46 57 M58 14L58 53 M70 17L70 50"/>
                      </g>
                      <text x="20" y="224" fill="#6f91ad" fontSize="7" letterSpacing="1">PLAN / SECTION</text>
                    </g>

                    <path d="M142 172H166" stroke="#67e8f9" strokeOpacity=".65" strokeWidth="1.5" strokeDasharray="3 4"/>
                    <path d="M160 167L167 172L160 177" fill="none" stroke="#67e8f9" strokeWidth="1.4"/>

                    <g className="grating-model-float" filter="url(#steelShadow)">
                      <polygon points="178,157 384,82 565,154 356,235" fill="#153c59" stroke="#80d9ed" strokeOpacity=".65" strokeWidth="1.2"/>
                      <polygon points="178,157 356,235 356,266 178,188" fill="url(#steelSide)" stroke="#4c9bbd" strokeOpacity=".65"/>
                      <polygon points="356,235 565,154 565,185 356,266" fill="#102d47" stroke="#4c9bbd" strokeOpacity=".65"/>

                      {Array.from({length:12},(_,i)=>(
                        <g key={`bearing-${i}`}>
                          <path d={`M${190+i*15.6} ${160-i*5.7} L${368+i*15.6} ${238-i*5.7} L${368+i*15.6} ${249-i*5.7} L${190+i*15.6} ${171-i*5.7} Z`} fill="url(#steelSide)" stroke="#6bb4d0" strokeOpacity=".65" strokeWidth=".65"/>
                          <path d={`M${190+i*15.6} ${160-i*5.7} L${368+i*15.6} ${238-i*5.7}`} stroke="url(#steelTop)" strokeWidth="5.5" strokeLinecap="butt"/>
                          <path d={`M${191+i*15.6} ${158-i*5.7} L${367+i*15.6} ${235-i*5.7}`} stroke="#e0f7ff" strokeOpacity=".36" strokeWidth=".8"/>
                        </g>
                      ))}

                      {Array.from({length:9},(_,i)=>(
                        <g key={`crossbar-${i}`}>
                          <path d={`M${187+i*22.5} ${153+i*9.1} L${394+i*19.1} ${78+i*8.5}`} stroke="#0a2034" strokeWidth="5" strokeLinecap="round"/>
                          <path d={`M${187+i*22.5} ${150+i*9.1} L${394+i*19.1} ${75+i*8.5}`} stroke="url(#crossSteel)" strokeWidth="3.2" strokeLinecap="round"/>
                          <path d={`M${187+i*22.5} ${149+i*9.1} L${394+i*19.1} ${74+i*8.5}`} stroke="#f0fdff" strokeOpacity=".45" strokeWidth=".7"/>
                        </g>
                      ))}
                      <path d="M178 157L384 82L565 154L356 235Z" fill="none" stroke="#b5f2ff" strokeOpacity=".62" strokeWidth="1.2"/>
                      <path d="M178 157L178 188L356 266L565 185L565 154" fill="none" stroke="#6bbbd8" strokeOpacity=".6" strokeWidth="1"/>
                      <path d="M178 157L356 235L565 154" fill="none" stroke="#d8f7ff" strokeOpacity=".25" strokeWidth="1"/>
                    </g>

                    <g className="ai-scan-beam">
                      <path d="M185 145L392 68L573 140L366 221Z" fill="url(#aiCore)" opacity=".18"/>
                      <path d="M190 148L396 73" stroke="#a5f3fc" strokeWidth="2" strokeOpacity=".75" filter="url(#cyanGlow)"/>
                    </g>
                    <g className="ai-analysis-orbit" transform="translate(474 158)">
                      <circle r="57" fill="url(#aiCore)"/>
                      <circle r="39" fill="none" stroke="#67e8f9" strokeOpacity=".5" strokeDasharray="3 6"/>
                      <circle r="27" fill="#0b2438" stroke="#67e8f9" strokeOpacity=".9" strokeWidth="1.4"/>
                      <path d="M-14 -5L0 -17L14 -5L0 7Z M-14 -5V9L0 21L14 9V-5 M0 7V21" fill="none" stroke="#b6f4ff" strokeWidth="1.7"/>
                      <circle r="3" fill="#efffff" filter="url(#cyanGlow)"/>
                    </g>
                    <text x="445" y="226" fill="#83ddec" fontSize="8" letterSpacing="1.1">AI RECOGNITION</text>
                    <path d="M529 158H565" stroke="#67e8f9" strokeOpacity=".8" strokeWidth="1.5" strokeDasharray="3 4"/>
                    <path d="M559 153L566 158L559 163" fill="none" stroke="#67e8f9" strokeWidth="1.4"/>

                    <g className="bom-output-card">
                      <rect x="574" y="45" width="315" height="270" rx="11" fill="url(#bomSurface)" stroke="#5b9bb6" strokeOpacity=".7"/>
                      <path d="M574 84H889" stroke="#5b9bb6" strokeOpacity=".45"/>
                      <text x="590" y="65" fill="#bceefa" fontSize="10" fontWeight="700" letterSpacing="1.5">GENERATED BILL OF MATERIALS</text>
                      <rect x="815" y="53" width="59" height="17" rx="4" fill="#164b5a" stroke="#48bfd0" strokeOpacity=".45"/>
                      <text x="844.5" y="64.5" fill="#9af0f4" fontSize="7" textAnchor="middle" letterSpacing=".8">PREVIEW</text>
                      <text x="590" y="78" fill="#718da7" fontSize="7.5" letterSpacing=".8">STEEL GRATING · STRUCTURED TAKEOFF</text>

                      <rect x="588" y="94" width="287" height="20" rx="3" fill="#1a3851"/>
                      <text x="596" y="107" fill="#8eacc4" fontSize="7" fontWeight="700">ITEM / SPECIFICATION</text>
                      <text x="816" y="107" fill="#8eacc4" fontSize="7" fontWeight="700" textAnchor="middle">QTY</text>
                      <text x="858" y="107" fill="#8eacc4" fontSize="7" fontWeight="700" textAnchor="middle">UNIT</text>

                      {[
                        ["Bearing bar","FB 30 × 3","24","m"],
                        ["Cross bar","Twisted Ø6","18","m"],
                        ["End band","FB 30 × 5","4","m"],
                        ["Support angle","L 40 × 40 × 4","6","m"],
                        ["Grating panel","G-01 / 1000×600","2","EA"]
                      ].map((row,i)=>(
                        <g key={row[0]}>
                          <rect x="588" y={118+i*31} width="287" height="30" fill={i%2===0?"#10263a":"#0c2032"} fillOpacity=".88"/>
                          <rect x="596" y={128+i*31} width="5" height="10" rx="1.5" fill={["#67e8f9","#60a5fa","#a78bfa","#5eead4","#93c5fd"][i]}/>
                          <text x="608" y={130+i*31} fill="#d6e8f5" fontSize="8.5" fontWeight="600">{row[0]}</text>
                          <text x="608" y={140+i*31} fill="#7895ae" fontSize="7.3">{row[1]}</text>
                          <text x="816" y={137+i*31} fill="#d5e9f7" fontSize="9" textAnchor="middle">{row[2]}</text>
                          <text x="858" y={137+i*31} fill="#8ba8c0" fontSize="8" textAnchor="middle">{row[3]}</text>
                          <path d={`M588 ${148+i*31}H875`} stroke="#47647c" strokeOpacity=".22"/>
                        </g>
                      ))}
                      <path d="M588 279H875" stroke="#5b9bb6" strokeOpacity=".4"/>
                      <circle cx="596" cy="294" r="3" fill="#5eead4"/>
                      <text x="606" y="297" fill="#82c9b7" fontSize="7.5" letterSpacing=".7">ITEMIZED OUTPUT · READY FOR REVIEW</text>
                    </g>
                  </svg>
                  <div className="scene-caption scene-caption-bottom"><span>2D DXF</span><i/><span>3D STEEL STRUCTURE</span><i/><span>AI TAKEOFF</span><i/><span>BOM TABLE</span></div>
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
