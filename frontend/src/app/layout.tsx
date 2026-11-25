import type { Metadata } from "next";
import "./globals.css";

import SessionExpiryHandler from "@/components/auth/session-expiry-handler";

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
        <SessionExpiryHandler />
        {children}
      </body>
    </html>
  );
}
