"use client";

import { createContext, useContext } from "react";
import type { User, UserManager } from "oidc-client-ts";

export const cognitoRegion =
  process.env.NEXT_PUBLIC_COGNITO_REGION ?? "us-east-1";
export const cognitoUserPoolId =
  process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID ?? "";
export const cognitoClientId = process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID ?? "";
export const cognitoDomain = process.env.NEXT_PUBLIC_COGNITO_DOMAIN ?? "";

export const cognitoAuthority = cognitoUserPoolId
  ? `https://cognito-idp.${cognitoRegion}.amazonaws.com/${cognitoUserPoolId}`
  : "";

export type Session = {
  token: string;
  email: string;
  name: string;
  expires: number;
};

type AuthState = {
  isLoading: boolean;
  session: Session | null;
  error: Error | null;
  signIn: () => Promise<void>;
  signOut: () => Promise<void>;
};

export const AuthStateContext = createContext<AuthState>({
  isLoading: false,
  session: null,
  error: null,
  signIn: async () => {
    throw new Error("Cognito sign-in is not configured.");
  },
  signOut: async () => {
    throw new Error("Cognito sign-in is not configured.");
  },
});

export function useAuthState() {
  return useContext(AuthStateContext);
}

export function useSession(): Session | null {
  return useAuthState().session;
}

let authManager: UserManager | null = null;

export function registerAuthManager(manager: UserManager) {
  authManager = manager;
}

export function unregisterAuthManager(manager: UserManager) {
  if (authManager === manager) authManager = null;
}

export async function getIdToken(): Promise<string | null> {
  if (!authManager) return null;
  const user = await authManager.getUser();
  if (!user || user.expired) return null;
  return user.id_token || null;
}

export async function signOut(): Promise<void> {
  await authManager?.removeUser();
}

export function cognitoLogoutUrl(origin: string): string {
  if (!cognitoClientId || !cognitoDomain) {
    throw new Error("Cognito logout is not configured.");
  }
  const domain = cognitoDomain.replace(/^https?:\/\//, "").replace(/\/+$/, "");
  const query = new URLSearchParams({
    client_id: cognitoClientId,
    logout_uri: `${origin}/`,
  });
  return `https://${domain}/logout?${query}`;
}

export function sessionFromUser(user: User | null | undefined): Session | null {
  if (!user || user.expired || !user.profile || !user.id_token) return null;
  const profile = user.profile;
  const email = typeof profile.email === "string" ? profile.email : "";
  if (!email) return null;

  return {
    token: user.id_token,
    email,
    name: typeof profile.name === "string" ? profile.name : email.split("@")[0],
    expires: (user.expires_at ?? 0) * 1000,
  };
}
