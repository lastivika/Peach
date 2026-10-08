"use client";
import Link from "next/link";

import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { useSession } from "@/lib/auth";

export default function LoginPage() {
  const session = useSession();

  return (
    <main className="relative mx-auto flex min-h-screen w-full max-w-lg flex-col justify-center gap-6 px-8">
      <div className="absolute top-6 right-0">
        <ThemeToggle />
      </div>
      <span className="text-5xl">🍑</span>
      <h1 className="font-heading text-4xl font-bold">Welcome to Peach</h1>
      <p className="text-muted-foreground">
        A little space for your plans. Sign in to keep your tasks together.
      </p>
      {session ? (
        <Button asChild>
          <Link href="/home">Open your workspace</Link>
        </Button>
      ) : (
        <Button asChild>
          <Link href="/login/">Sign in or create an account</Link>
        </Button>
      )}
    </main>
  );
}
