"use client";
import Link from "next/link";
import { SiteHeader } from "@/components/site-header";
import { useSession } from "@/lib/auth";
export default function AppLayout({ children }: { children: React.ReactNode }) {
  const session = useSession();
  if (!session)
    return (
      <main className="mx-auto p-12">
        <Link href="/">Sign in to open your workspace →</Link>
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
