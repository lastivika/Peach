"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { ThemeToggle } from "@/components/theme-toggle";
import {
  cognitoAuthority,
  cognitoClientId,
  cognitoDomain,
  useAuthState,
} from "@/lib/auth";
import { Button } from "@/components/ui/button";

export default function LoginPage() {
  const auth = useAuthState();
  const router = useRouter();
  const started = useRef(false);
  const [error, setError] = useState("");
  const configured = Boolean(
    cognitoAuthority && cognitoClientId && cognitoDomain,
  );

  useEffect(() => {
    if (auth.isLoading || !configured || auth.error || started.current) return;
    if (auth.session) {
      router.replace("/home");
      return;
    }
    started.current = true;
    void auth.signIn().catch((cause: unknown) => {
      setError(
        cause instanceof Error ? cause.message : "Could not start sign-in.",
      );
    });
  }, [auth, configured, router]);

  return (
    <main className="relative mx-auto flex min-h-screen w-full max-w-lg flex-col justify-center gap-6 px-8">
      <div className="absolute top-6 right-0">
        <ThemeToggle />
      </div>
      <Link href="/" className="text-5xl" aria-label="Peach home">
        🍑
      </Link>
      <h1 className="font-heading text-4xl font-bold">Sign in to Peach</h1>
      <p className="text-muted-foreground">
        Continue with your Peach account. Sign-in is securely hosted by Cognito.
      </p>
      {!configured ? (
        <p role="alert">
          Cognito sign-in is not configured. Set the frontend Cognito user pool
          ID, client ID, and domain before building.
        </p>
      ) : auth.error || error ? (
        <>
          <p role="alert">
            Could not start sign-in: {error || auth.error?.message}
          </p>
          <Button
            onClick={() => {
              setError("");
              started.current = true;
              void auth.signIn().catch((cause: unknown) => {
                setError(
                  cause instanceof Error
                    ? cause.message
                    : "Could not start sign-in.",
                );
              });
            }}
          >
            Try sign in again
          </Button>
          <Link href="/">Back to Peach</Link>
        </>
      ) : (
        <p>Opening secure sign-in…</p>
      )}
    </main>
  );
}
