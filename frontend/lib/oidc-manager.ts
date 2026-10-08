import { UserManager, WebStorageStateStore } from "oidc-client-ts";

type OidcManagerOptions = {
  authority: string;
  clientId: string;
  redirectUri: string;
  storage: Storage;
};

export function createOidcManager({
  authority,
  clientId,
  redirectUri,
  storage,
}: OidcManagerOptions): UserManager {
  const sessionStore = new WebStorageStateStore({ store: storage });

  return new UserManager({
    authority,
    client_id: clientId,
    redirect_uri: redirectUri,
    response_type: "code",
    scope: "openid email profile",
    automaticSilentRenew: true,
    stateStore: sessionStore,
    userStore: sessionStore,
  });
}
