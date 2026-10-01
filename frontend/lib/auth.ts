"use client";
import { useSyncExternalStore } from "react";
const clientId = process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID ?? "";
const domain = process.env.NEXT_PUBLIC_COGNITO_DOMAIN ?? "";
type Session = { token: string; email: string; name: string; expires: number };
let cached: Session | null = null;
let loaded = false;
const listeners = new Set<() => void>();
function publish(value: Session | null) {
  cached = value;
  loaded = true;
  if (value) sessionStorage.setItem("peach-session", JSON.stringify(value));
  else sessionStorage.removeItem("peach-session");
  listeners.forEach((fn) => fn());
}
function snapshot() {
  if (!loaded && typeof window !== "undefined") {
    loaded = true;
    try {
      cached = JSON.parse(sessionStorage.getItem("peach-session") ?? "null");
    } catch {
      cached = null;
    }
  }
  return cached;
}
export function useSession() {
  return useSyncExternalStore(
    (fn) => {
      listeners.add(fn);
      return () => {
        listeners.delete(fn);
      };
    },
    snapshot,
    () => null,
  );
}
export async function getIdToken() {
  const session = snapshot();
  if (!session || session.expires <= Date.now()) return null;
  return session.token;
}
export function signOut() {
  publish(null);
}
function base64url(bytes: Uint8Array) {
  return btoa(String.fromCharCode(...bytes))
    .replaceAll("+", "-")
    .replaceAll("/", "_")
    .replaceAll("=", "");
}
export async function signIn() {
  if (!clientId || !domain) throw new Error("Sign-in is not configured yet.");
  const verifier = base64url(crypto.getRandomValues(new Uint8Array(32)));
  const state = base64url(crypto.getRandomValues(new Uint8Array(24)));
  const nonce = base64url(crypto.getRandomValues(new Uint8Array(24)));
  sessionStorage.setItem(
    "peach-oauth",
    JSON.stringify({ verifier, state, nonce }),
  );
  const challenge = base64url(
    new Uint8Array(
      await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier)),
    ),
  );
  const query = new URLSearchParams({
    client_id: clientId,
    response_type: "code",
    scope: "openid email profile",
    redirect_uri: location.origin + "/callback",
    code_challenge_method: "S256",
    code_challenge: challenge,
    state,
    nonce,
  });
  location.assign(`https://${domain}/oauth2/authorize?${query}`);
}
export async function completeSignIn() {
  const query = new URLSearchParams(location.search);
  const raw = sessionStorage.getItem("peach-oauth");
  if (!raw) throw new Error("Login session expired. Please sign in again.");
  const saved = JSON.parse(raw);
  if (!query.get("code") || query.get("state") !== saved.state)
    throw new Error("Login verification failed.");
  sessionStorage.removeItem("peach-oauth");
  const response = await fetch(`https://${domain}/oauth2/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "authorization_code",
      client_id: clientId,
      code: query.get("code")!,
      redirect_uri: location.origin + "/callback",
      code_verifier: saved.verifier,
    }),
  });
  if (!response.ok)
    throw new Error("Could not complete sign-in. Please try again.");
  const tokens = await response.json();
  // Claims here are display-only. The API independently verifies signatures and claims.
  const part = tokens.id_token
    .split(".")[1]
    .replaceAll("-", "+")
    .replaceAll("_", "/");
  const claims = JSON.parse(
    new TextDecoder().decode(
      Uint8Array.from(atob(part), (c) => c.charCodeAt(0)),
    ),
  );
  if (
    claims.nonce !== saved.nonce ||
    claims.aud !== clientId ||
    claims.token_use !== "id"
  )
    throw new Error("Login verification failed.");
  publish({
    token: tokens.id_token,
    email: claims.email,
    name: claims.name ?? claims.email.split("@")[0],
    expires: claims.exp * 1000,
  });
  history.replaceState(null, "", "/callback");
}
