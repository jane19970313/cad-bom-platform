"use client";

import { useState } from "react";
import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity, ChevronLeft, ChevronRight, FileCode2, FolderKanban,
  Layers3, LayoutDashboard, Menu, Workflow, X,
} from "lucide-react";
import UserMenu from "@/components/dashboard/user-menu";

const navigation = [
  { label: "Overview", href: "/", icon: LayoutDashboard },
  { label: "Projects", href: "/projects", icon: FolderKanban },
  { label: "Drawings", href: "/drawings", icon: FileCode2 },
  { label: "Processing jobs", href: "/pipeline", icon: Workflow },
];

function isWorkspacePath(pathname: string) {
  return pathname === "/" || ["/projects", "/drawings", "/pipeline", "/jobs"].some(
    (path) => pathname === path || pathname.startsWith(path + "/"),
  );
}

export default function WorkspaceShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  if (!isWorkspacePath(pathname)) return <>{children}</>;

  const current = navigation.find((item) =>
    item.href === "/" ? pathname === "/" : pathname === item.href || pathname.startsWith(item.href + "/"),
  ) ?? navigation[0];
  const PageIcon = current.icon;

  return (
    <div className={`app-shell ${collapsed ? "app-shell-collapsed" : ""}`}>
      {mobileOpen && <button aria-label="Close navigation" className="app-mobile-scrim" onClick={() => setMobileOpen(false)} />}
      <aside className={`app-sidebar ${collapsed ? "is-collapsed" : ""} ${mobileOpen ? "is-mobile-open" : ""}`}>
        <div className="app-brand-row">
          <Link href="/" className="app-brand" onClick={() => setMobileOpen(false)}>
            <span className="app-brand-mark"><Layers3 size={21}/></span>
            <span className="app-brand-copy"><strong>CAD2BOM</strong><small>ENGINEERING WORKSPACE</small></span>
          </Link>
          <button className="app-sidebar-collapse" onClick={() => setCollapsed((value) => !value)} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"} title={collapsed ? "Expand sidebar" : "Collapse sidebar"}>
            {collapsed ? <ChevronRight size={16}/> : <ChevronLeft size={16}/>}
          </button>
          <button className="app-mobile-close" onClick={() => setMobileOpen(false)} aria-label="Close navigation"><X size={18}/></button>
        </div>
        <div className="app-nav-caption">WORKSPACE</div>
        <nav className="app-navigation" aria-label="Main navigation">
          {navigation.map(({label,href,icon:Icon}) => {
            const active = href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(href + "/");
            return <Link key={href} href={href} onClick={() => setMobileOpen(false)} aria-current={active ? "page" : undefined} title={collapsed ? label : undefined} className={`app-nav-link ${active ? "is-active" : ""}`}>
              <Icon size={18}/><span>{label}</span>{active && <i/>}
            </Link>;
          })}
        </nav>
        <div className="app-sidebar-bottom">
          <div className="app-system-indicator"><span/><span className="app-system-copy">ENGINEERING SYSTEM ONLINE</span></div>
          <div className="app-sidebar-version">CAD2BOM <span>·</span> WORKSPACE</div>
        </div>
      </aside>

      <div className="app-main-column">
        <header className="app-topbar">
          <div className="app-topbar-left">
            <button className="app-mobile-menu" onClick={() => setMobileOpen(true)} aria-label="Open navigation"><Menu size={19}/></button>
            <div className="app-page-context">
              <div className="app-breadcrumb"><span>CAD2BOM</span><i>/</i><span>WORKSPACE</span></div>
              <div className="app-page-title"><PageIcon size={15}/>{current.label}</div>
            </div>
          </div>
          <div className="app-topbar-right">
            <div className="app-connection-state"><span/> API CONNECTED</div>
            <UserMenu/>
          </div>
        </header>

        <main className="app-content">{children}</main>
        <footer className="app-footer">
          <span>CAD2BOM <i>·</i> ENGINEERING WORKSPACE</span>
          <span>DRAWING INTELLIGENCE <i>·</i> GEOMETRY ANALYSIS <i>·</i> BILL OF MATERIALS</span>
        </footer>
      </div>
    </div>
  );
}
