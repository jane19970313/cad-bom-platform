"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function SessionExpiryHandler() {
  const router = useRouter();

  useEffect(() => {
    function handleSessionExpired() {
      const currentPath =
        window.location.pathname + window.location.search;

      const next = encodeURIComponent(currentPath);

      router.replace(`/login?reason=session-expired&next=${next}`);
    }

    window.addEventListener(
      "dxf2bom:session-expired",
      handleSessionExpired,
    );

    return () => {
      window.removeEventListener(
        "dxf2bom:session-expired",
        handleSessionExpired,
      );
    };
  }, [router]);

  return null;
}