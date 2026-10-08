"use client";
import { useEffect } from "react";

export default function CallbackPage() {
  useEffect(() => {
    window.location.replace(
      `/auth/callback/${window.location.search}${window.location.hash}`,
    );
  }, []);

  return (
    <main className="mx-auto max-w-lg p-12">
      <p>Continuing sign-in…</p>
    </main>
  );
}
