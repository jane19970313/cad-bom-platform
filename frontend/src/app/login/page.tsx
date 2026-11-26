"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { ApiError, authApi } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [sessionExpired, setSessionExpired] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setSessionExpired(params.get("reason") === "session-expired");
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setLoading(true);
    setError("");

    try {
      await authApi.login(email, password);

      // Confirm that the returned token is accepted by the backend.
      await authApi.getCurrentUser<unknown>();

      const params = new URLSearchParams(window.location.search);
      const requestedPath = params.get("next");

      const destination =
        requestedPath &&
        requestedPath.startsWith("/") &&
        !requestedPath.startsWith("//")
          ? requestedPath
          : "/";

      router.replace(destination);
      router.refresh();
    } catch (err) {
      // authApi.logout();

      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Unable to connect to the backend. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#080f1d] px-4 py-12 text-slate-100">
      <div className="w-full max-w-md rounded-xl border border-cyan-300/15 bg-[#0d192a] p-8 shadow-[0_24px_80px_rgba(0,0,0,.38)]">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold tracking-tight text-slate-50">
            DXF to BOM Platform
          </h1>
          <p className="mt-2 text-sm text-slate-400">
            Sign in to access your engineering workspace.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label
              htmlFor="email"
              className="mb-2 block text-sm font-medium text-slate-300"
            >
              Email address
            </label>
            <input
              id="email"
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
              className="w-full rounded-md border border-white/10 bg-[#081321] px-3 py-2.5 text-sm text-slate-100 placeholder:text-slate-600 outline-none focus:border-cyan-300/50 focus:ring-2 focus:ring-cyan-300/10"
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="mb-2 block text-sm font-medium text-slate-300"
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Enter your password"
              className="w-full rounded-md border border-white/10 bg-[#081321] px-3 py-2.5 text-sm text-slate-100 placeholder:text-slate-600 outline-none focus:border-cyan-300/50 focus:ring-2 focus:ring-cyan-300/10"
            />
          </div>

          {sessionExpired && (
            <div
              role="status"
              className="rounded-md border border-amber-300/20 bg-amber-300/10 p-3 text-sm text-amber-100"
            >
              <p className="font-semibold">Your session has expired</p>
              <p className="mt-1">
                Please sign in again to continue. After signing in,
                you will be returned to your previous page.
              </p>
            </div>
          )}

          {error && (
            <div
              role="alert"
              className="rounded-md border border-rose-300/20 bg-rose-300/10 p-3 text-sm text-rose-200"
            >
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-gradient-to-r from-blue-500 to-cyan-400 px-4 py-2.5 text-sm font-semibold text-[#06111f] transition hover:from-blue-400 hover:to-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-400">
          New to CAD2BOM?{" "}
          <a href="/register" className="font-semibold text-cyan-700 hover:text-cyan-500">
            Create an account
          </a>
        </p>

        <p className="mt-6 text-center text-xs text-slate-400">
          Secure access to your DXF processing workspace.
        </p>
      </div>
    </main>
  );
}