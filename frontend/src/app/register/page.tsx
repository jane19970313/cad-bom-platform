"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ApiError, authApi } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setError("");
    setSuccess("");

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    if (password.length < 4 || password.length > 128) {
      setError("Password must be between 4 and 128 characters.");
      return;
    }

    setLoading(true);

    try {
      await authApi.register({
        email: email.trim().toLowerCase(),
        password,
      });

      setSuccess("Account created. Signing you in...");
      await authApi.login(email.trim().toLowerCase(), password);
      await authApi.getCurrentUser<unknown>();
      router.replace("/");
      router.refresh();
    } catch (err) {
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

        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold tracking-tight text-slate-50">
            DXF to BOM Platform
          </h1>

          <p className="mt-2 text-sm text-slate-400">
            Create an account to access your engineering workspace.
          </p>
        </div>

        {/* Registration Form */}
        <form onSubmit={handleSubmit} className="space-y-5">

          {/* Email */}
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
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
              className="w-full rounded-md border border-white/10 bg-[#081321] px-3 py-2.5 text-sm text-slate-100 placeholder:text-slate-600 outline-none focus:border-cyan-300/50 focus:ring-2 focus:ring-cyan-300/10"
            />
          </div>

          {/* Password */}
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
              autoComplete="new-password"
              required
              minLength={4}
              maxLength={128}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Create a password"
              className="w-full rounded-md border border-white/10 bg-[#081321] px-3 py-2.5 text-sm text-slate-100 placeholder:text-slate-600 outline-none focus:border-cyan-300/50 focus:ring-2 focus:ring-cyan-300/10"
            />

            <p className="mt-1 text-xs text-slate-400">
              Password must be between 4 and 128 characters.
            </p>
          </div>

          {/* Confirm Password */}
          <div>
            <label
              htmlFor="confirmPassword"
              className="mb-2 block text-sm font-medium text-slate-300"
            >
              Confirm password
            </label>

            <input
              id="confirmPassword"
              type="password"
              autoComplete="new-password"
              required
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              placeholder="Confirm your password"
              className="w-full rounded-md border border-white/10 bg-[#081321] px-3 py-2.5 text-sm text-slate-100 placeholder:text-slate-600 outline-none focus:border-cyan-300/50 focus:ring-2 focus:ring-cyan-300/10"
            />
          </div>

          {/* Error */}
          {error && (
            <div
              role="alert"
              className="rounded-md border border-rose-300/20 bg-rose-300/10 p-3 text-sm text-rose-200"
            >
              {error}
            </div>
          )}

          {/* Success */}
          {success && (
            <div
              role="status"
              className="rounded-md border border-emerald-300/20 bg-emerald-300/10 p-3 text-sm text-emerald-200"
            >
              {success}
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-gradient-to-r from-blue-500 to-cyan-400 px-4 py-2.5 text-sm font-semibold text-[#06111f] transition hover:from-blue-400 hover:to-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? "Creating account..." : "Create account"}
          </button>
        </form>

        {/* Login Link */}
        <p className="mt-6 text-center text-sm text-slate-400">
          Already have an account?{" "}
          <Link
            href="/login"
            className="font-semibold text-slate-50 hover:text-slate-600"
          >
            Sign in
          </Link>
        </p>

        <p className="mt-4 text-center text-xs text-slate-400">
          Secure access to your DXF processing workspace.
        </p>
      </div>
    </main>
  );
}