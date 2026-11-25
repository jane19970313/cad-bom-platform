"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  ChevronDown,
  LogOut,
  UserRound,
} from "lucide-react";

import { authApi } from "@/lib/api";
import { ApiError } from "@/lib/api/client";
import type { UserResponse } from "@/types/auth";

export default function UserMenu() {
  const router = useRouter();

  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [menuOpen, setMenuOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loggingOut, setLoggingOut] = useState(false);

  async function loadUser() {
    setLoading(true);
    setError(null);

    try {
      const currentUser =
        await authApi.getCurrentUser<UserResponse>();

      setUser(currentUser);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        await authApi.logout();
        router.replace("/login");
        return;
      }

      setError(
        err instanceof Error
          ? err.message
          : "Unable to load your account. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let active = true;

    async function initialize() {
      try {
        const currentUser =
          await authApi.getCurrentUser<UserResponse>();

        if (active) {
          setUser(currentUser);
          setError(null);
        }
      } catch (err) {
        if (!active) return;

        if (err instanceof ApiError && err.status === 401) {
          await authApi.logout();

          if (active) {
            router.replace("/login");
          }
        } else {
          setError(
            err instanceof Error
              ? err.message
              : "Unable to load your account.",
          );
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    initialize();

    return () => {
      active = false;
    };
  }, [router]);

  async function handleLogout() {
    if (loggingOut) return;

    setLoggingOut(true);

    try {
      await authApi.logout();
    } finally {
      router.replace("/login");
      router.refresh();
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 rounded-lg border px-3 py-2 text-sm text-muted-foreground">
        <UserRound className="h-4 w-4" />
        Loading account...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex max-w-sm items-center gap-2 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
        <AlertCircle className="h-4 w-4 shrink-0" />
        <span className="min-w-0 flex-1">{error}</span>
        <button
          type="button"
          onClick={loadUser}
          className="shrink-0 font-medium underline"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  const initial = user.email.charAt(0).toUpperCase();

  return (
    <div className="user-menu relative">
      <button
        type="button"
        onClick={() => setMenuOpen((open) => !open)}
        className="user-menu-trigger flex items-center gap-3 rounded-xl border px-3 py-2 text-left transition hover:border-cyan-300/30 hover:bg-white/[0.06]"
      >
        <span className="user-menu-avatar flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold">
          {initial}
        </span>

        <span className="hidden min-w-0 sm:block">
          <span className="block text-sm font-medium">
            {user.email}
          </span>
          <span className="block text-xs text-muted-foreground">
            Signed in
          </span>
        </span>

        <ChevronDown className="h-4 w-4 text-muted-foreground" />
      </button>

      {menuOpen && (
        <div className="user-menu-popover absolute right-0 z-50 mt-2 w-56 rounded-xl border p-2 shadow-2xl">
          <div className="border-b border-white/10 px-3 py-2">
            <p className="text-xs text-muted-foreground">
              Signed in as
            </p>
            <p className="truncate text-sm font-medium">
              {user.email}
            </p>
          </div>

          <button
            type="button"
            onClick={handleLogout}
            disabled={loggingOut}
            className="mt-1 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-rose-300 transition hover:bg-rose-400/10 disabled:opacity-50"
          >
            <LogOut className="h-4 w-4" />
            {loggingOut ? "Logging out..." : "Log out"}
          </button>
        </div>
      )}
    </div>
  );
}