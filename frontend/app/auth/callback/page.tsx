"use client";

import Link from "next/link";

import { useAuthState } from "@/lib/auth";

export default function AuthCallbackPage() {
  const auth = useAuthState();

  return (
    <main className="mx-auto max-w-lg p-12">
      {auth.error ? (
        <>
          <p role="alert">Sign-in failed: {auth.error.message}</p>
          <Link href="/login/">Back to sign in</Link>
        </>
      ) : (
        <p>Completing sign-in…</p>
      )}
    </main>
  );
}
