"use client";
import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { signIn, useSession } from "@/lib/auth";
export default function LoginPage() {
  const session = useSession();
  const [error, setError] = useState("");
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-lg flex-col justify-center gap-6 px-8">
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
        <Button onClick={() => void signIn().catch((e) => setError(e.message))}>
          Sign in or create an account
        </Button>
      )}
      {error && <p role="alert">{error}</p>}
    </main>
  );
}
