"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { completeSignIn } from "@/lib/auth";
export default function CallbackPage() {
  const started = useRef(false);
  const [error, setError] = useState("");
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    void completeSignIn()
      .then(() => location.replace("/home"))
      .catch((e) => setError(e.message));
  }, []);
  return (
    <main className="mx-auto max-w-lg p-12">
      {error ? (
        <>
          <p role="alert">{error}</p>
          <Link href="/">Back to sign in</Link>
        </>
      ) : (
        <p>Completing sign-in…</p>
      )}
    </main>
  );
}
