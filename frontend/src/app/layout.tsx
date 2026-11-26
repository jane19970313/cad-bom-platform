import type { Metadata } from "next";
import "./globals.css";

import SessionExpiryHandler from "@/components/auth/session-expiry-handler";
import { LocaleProvider } from "@/components/i18n/locale-provider";
import LanguageSwitcher from "@/components/i18n/language-switcher";
import WorkspaceShell from "@/components/dashboard/workspace-shell";

export const metadata: Metadata = {
  title: {
    default: "CAD2BOM | Engineering Workspace",
    template: "%s | CAD2BOM",
  },
  description:
    "An engineering workspace for DXF drawing analysis, geometry inspection and bill of materials generation.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">
        <LocaleProvider>
          <SessionExpiryHandler />
          <div className="fixed right-4 top-20 z-[100]" data-i18n-ignore="true">
            <LanguageSwitcher />
          </div>
          <WorkspaceShell>{children}</WorkspaceShell>
        </LocaleProvider>
      </body>
    </html>
  );
}
