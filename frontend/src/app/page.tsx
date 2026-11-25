import {
  Activity,
  ArrowDownRight,
  ArrowRight,
  Box,
  CheckCircle2,
  ChevronDown,
  CircleHelp,
  Clock3,
  FileCode2,
  FileText,
  FolderKanban,
  Gauge,
  Layers3,
  LayoutDashboard,
  Plus,
  Settings2,
  ShieldCheck,
  TriangleAlert,
  Upload,
  Workflow,
} from "lucide-react";
import type { ElementType } from "react";
import UserMenu from "@/components/dashboard/user-menu";
import DashboardData from "@/components/dashboard/dashboard-data";

const pipelineStages = [
  { name: "File validation", detail: "Check DXF file and metadata", status: "Ready" },
  { name: "Entity extraction", detail: "Read modelspace entities", status: "Ready" },
  { name: "Geometry conversion", detail: "Convert entities to geometry", status: "Ready" },
  { name: "Spatial analysis", detail: "Build spatial index", status: "Pending" },
  { name: "Topology analysis", detail: "Detect geometric relationships", status: "Pending" },
  { name: "Engineering classification", detail: "Classify structural elements", status: "Pending" },
  { name: "BOM generation", detail: "Group parts and calculate quantities", status: "Pending" },
];

const drawings = [
  {
    name: "Steel platform - Level 01.dxf",
    project: "Steel Platform Project",
    entities: "689",
    status: "Completed",
    date: "Today",
  },
  {
    name: "Main frame assembly.dxf",
    project: "Factory Extension",
    entities: "—",
    status: "Not started",
    date: "Yesterday",
  },
  {
    name: "Equipment support detail.dxf",
    project: "Steel Platform Project",
    entities: "—",
    status: "Not started",
    date: "Yesterday",
  },
];

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    Completed: "bg-emerald-50 text-emerald-700",
    Ready: "bg-emerald-50 text-emerald-700",
    Pending: "bg-slate-100 text-slate-500",
    "Not started": "bg-slate-100 text-slate-500",
    Processing: "bg-blue-50 text-blue-700",
    Failed: "bg-red-50 text-red-700",
  };

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${
        styles[status] ?? "bg-slate-100 text-slate-600"
      }`}
    >
      {status}
    </span>
  );
}

function SidebarLink({
  icon: Icon,
  label,
  active = false,
  href = "#",
}: {
  icon: ElementType;
  label: string;
  active?: boolean;
  href?: string;
}) {
  return (
    <a
      href={href}
      className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition ${
        active
          ? "bg-blue-50 font-semibold text-blue-700"
          : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
      }`}
    >
      <Icon size={18} />
      {label}
    </a>
  );
}

export default function DashboardPage() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="flex min-h-screen">
        {/* Sidebar */}
        <aside className="hidden w-64 shrink-0 border-r border-slate-200 bg-white px-4 py-6 md:flex md:flex-col">
          <div className="mb-9 flex items-center gap-3 px-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white">
              <Layers3 size={22} />
            </div>
            <div>
              <h1 className="text-base font-bold tracking-tight">DXF2BOM</h1>
              <p className="text-xs text-slate-500">Engineering Workbench</p>
            </div>
          </div>

          <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
            Workspace
          </p>
          <nav className="space-y-1">
            <SidebarLink
              icon={LayoutDashboard}
              label="Dashboard"
              active
              href="/"
            />

            <SidebarLink
              icon={FolderKanban}
              label="Projects"
              href="/projects"
            />

            <SidebarLink
              icon={FileCode2}
              label="Drawings"
              href="/drawings"
            />

            <SidebarLink
              icon={Workflow}
              label="Processing Jobs"
              href="/pipeline"
            />
          </nav>

          <p className="mb-2 mt-8 px-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
            Engineering
          </p>
          <nav className="space-y-1">
            <SidebarLink icon={Box} label="Geometry Inspector" />
            <SidebarLink
              icon={Activity}
              label="Pipeline Monitor"
              href="/pipeline"
            />
            <SidebarLink icon={FileText} label="BOM Results" />
          </nav>

          <div className="mt-auto space-y-1 border-t border-slate-100 pt-5">
            <SidebarLink icon={Settings2} label="Settings" />
            <SidebarLink icon={CircleHelp} label="Help & Documentation" />
          </div>
        </aside>

        {/* Main content */}
        <section className="min-w-0 flex-1">
          {/* Top bar */}
          <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-5 md:px-8">
            <div>
              <p className="text-sm text-slate-500">Workspace / Overview</p>
            </div>
            <div className="flex items-center gap-3">
              <span className="hidden rounded-full bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-700 sm:inline-flex">
                Prototype data
              </span>
              <UserMenu />
            </div>
          </header>

          <div className="mx-auto max-w-7xl space-y-7 p-5 md:p-8">
            {/* Page heading */}
            <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
              <div>
                <h2 className="text-2xl font-bold tracking-tight">Dashboard</h2>
                <p className="mt-1 text-sm text-slate-500">
                  Monitor DXF extraction, engineering analysis and BOM generation.
                </p>
              </div>
              <a
                href="/drawings"
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-700"
              >
                <Plus size={17} />
                New drawing
              </a>
            </div>

            {/* Prototype notice */}
            {/* <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4">
              <TriangleAlert className="mt-0.5 shrink-0 text-amber-600" size={19} />
              <div>
                <p className="text-sm font-semibold text-amber-900">
                  Frontend prototype — not connected to the backend yet
                </p>
                <p className="mt-1 text-sm text-amber-800">
                  The values and statuses on this screen are illustrative. Live job
                  status, pipeline stages and analysis results will appear after API
                  integration.
                </p>
              </div>
            </div> */}

            {/* Summary cards */}
            <DashboardData />

            {/* Pipeline and drawing list */}
            {/* <div className="grid gap-6">
              <div className="rounded-xl border border-slate-200 bg-white p-5">
                <div className="mb-5 flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold">Analysis pipeline</h3>
                    <p className="mt-1 text-xs text-slate-500">
                      Planned processing stages
                    </p>
                  </div>
                  <Workflow className="text-slate-400" size={20} />
                </div>

                <div className="space-y-4">
                  {pipelineStages.map((stage, index) => (
                    <div key={stage.name} className="flex gap-3">
                      <div className="flex flex-col items-center">
                        <div
                          className={`flex h-7 w-7 items-center justify-center rounded-full ${
                            stage.status === "Ready"
                              ? "bg-emerald-100 text-emerald-700"
                              : "bg-slate-100 text-slate-400"
                          }`}
                        >
                          {stage.status === "Ready" ? (
                            <CheckCircle2 size={16} />
                          ) : (
                            <span className="text-xs font-semibold">{index + 1}</span>
                          )}
                        </div>
                        {index !== pipelineStages.length - 1 && (
                          <div className="mt-1 h-5 w-px bg-slate-200" />
                        )}
                      </div>
                      <div className="min-w-0 flex-1 pb-1">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <p className="text-sm font-medium">{stage.name}</p>
                          <StatusBadge status={stage.status} />
                        </div>
                        <p className="mt-1 text-xs text-slate-500">{stage.detail}</p>
                      </div>
                    </div>
                  ))}
                </div>

                <p className="mt-5 border-t border-slate-100 pt-4 text-xs text-slate-400">
                  These are workflow definitions, not live execution states.
                </p>
              </div>
            </div> */}

            {/* Next implementation targets */}
            <div className="rounded-xl border border-slate-200 bg-white p-5">
              <div className="mb-4 flex items-center gap-2">
                <Gauge className="text-blue-600" size={20} />
                <h3 className="font-semibold">Engineering inspection modules</h3>
              </div>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <ModuleCard icon={FileText} title="Entity extraction" description="Inspect DXF entities, layers and handles." />
                <ModuleCard icon={Layers3} title="Geometry conversion" description="Inspect converted geometry and warnings." />
                <ModuleCard icon={Activity} title="Topology analysis" description="Inspect nodes, edges and relationships." />
                <ModuleCard icon={ShieldCheck} title="Classification & BOM" description="Review engineering types and quantities." />
              </div>
            </div>

            <footer className="flex flex-col gap-2 border-t border-slate-200 pt-5 text-xs text-slate-400 sm:flex-row sm:justify-between">
              <span>DXF2BOM Engineering Workbench</span>
              <span>Frontend prototype · Backend integration pending</span>
            </footer>
          </div>
        </section>
      </div>
    </main>
  );
}

function SummaryCard({
  label,
  value,
  description,
  icon: Icon,
}: {
  label: string;
  value: string;
  description: string;
  icon: ElementType;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-slate-500">{label}</p>
        <div className="rounded-lg bg-slate-100 p-2 text-slate-600">
          <Icon size={18} />
        </div>
      </div>
      <p className="mt-4 text-3xl font-bold tracking-tight">{value}</p>
      <p className="mt-1 text-xs text-slate-400">{description}</p>
    </div>
  );
}

function ModuleCard({
  icon: Icon,
  title,
  description,
}: {
  icon: ElementType;
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-lg border border-slate-200 p-4 transition hover:border-blue-300 hover:bg-blue-50/30">
      <Icon size={20} className="mb-3 text-blue-600" />
      <p className="text-sm font-semibold">{title}</p>
      <p className="mt-1 text-xs leading-5 text-slate-500">{description}</p>
    </div>
  );
}
