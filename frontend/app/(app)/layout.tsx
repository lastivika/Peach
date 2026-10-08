"use client";
import Link from "next/link";

import { SiteHeader } from "@/components/site-header";
import { ThemeToggle } from "@/components/theme-toggle";
import { useAuthState } from "@/lib/auth";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const auth = useAuthState();
  const session = auth.session;

  if (auth.isLoading)
    return <main className="mx-auto p-12">Loading session…</main>;

  if (!session)
    return (
      <main className="mx-auto flex min-h-screen flex-col gap-6 p-12">
        <div className="flex justify-end">
          <ThemeToggle />
        </div>
        {auth.error && (
          <p className="text-sm text-destructive" role="alert">
            Sign-in issue: {auth.error.message}
          </p>
        )}
        <Link href="/login/">Sign in to open your workspace →</Link>
      </main>
    );
  return (
    <>
      <SiteHeader />
      <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-10 sm:px-8">
        {children}
      </main>
    </>
  );
}
