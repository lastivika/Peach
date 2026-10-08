"use client";

import { AuthProvider as OidcAuthProvider, useAuth } from "react-oidc-context";
import type { UserManager } from "oidc-client-ts";
import { useEffect, useMemo, useState } from "react";

import {
  AuthStateContext,
  cognitoAuthority,
  cognitoClientId,
  cognitoDomain,
  cognitoLogoutUrl,
  registerAuthManager,
  sessionFromUser,
  unregisterAuthManager,
} from "@/lib/auth";
import { createOidcManager } from "@/lib/oidc-manager";

function OidcStateBridge({ children }: { children: React.ReactNode }) {
  const auth = useAuth();
  const state = useMemo(
    () => ({
      isLoading: auth.isLoading,
      session: sessionFromUser(auth.user),
      error: auth.error ?? null,
      signIn: async () => {
        await auth.signinRedirect();
      },
      signOut: async () => {
        await auth.removeUser();
        window.location.assign(cognitoLogoutUrl(window.location.origin));
      },
    }),
    [auth],
  );

  return (
    <AuthStateContext.Provider value={state}>
      {children}
    </AuthStateContext.Provider>
  );
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [manager, setManager] = useState<UserManager | null>(null);
  const configured = Boolean(
    cognitoAuthority && cognitoClientId && cognitoDomain,
  );

  useEffect(() => {
    if (!configured) return;

    const userManager = createOidcManager({
      authority: cognitoAuthority,
      clientId: cognitoClientId,
      redirectUri: `${window.location.origin}/auth/callback/`,
      storage: window.sessionStorage,
    });
    registerAuthManager(userManager);
    const timer = window.setTimeout(() => setManager(userManager), 0);

    return () => {
      window.clearTimeout(timer);
      unregisterAuthManager(userManager);
    };
  }, [configured]);

  if (!configured) {
    return (
      <AuthStateContext.Provider
        value={{
          isLoading: false,
          session: null,
          error: new Error(
            "Cognito sign-in is not configured. Set the Cognito user pool ID, client ID, and domain.",
          ),
          signIn: async () => {
            throw new Error("Cognito sign-in is not configured.");
          },
          signOut: async () => {
            throw new Error("Cognito sign-in is not configured.");
          },
        }}
      >
        {children}
      </AuthStateContext.Provider>
    );
  }

  if (!manager) {
    return (
      <AuthStateContext.Provider
        value={{
          isLoading: true,
          session: null,
          error: null,
          signIn: async () => {
            throw new Error("Cognito sign-in is initializing.");
          },
          signOut: async () => {
            throw new Error("Cognito sign-in is initializing.");
          },
        }}
      >
        {children}
      </AuthStateContext.Provider>
    );
  }

  return (
    <OidcAuthProvider
      userManager={manager}
      onSigninCallback={() => {
        window.history.replaceState({}, document.title, "/auth/callback/");
        window.location.replace("/home");
      }}
    >
      <OidcStateBridge>{children}</OidcStateBridge>
    </OidcAuthProvider>
  );
}
