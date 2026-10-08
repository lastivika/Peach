import { beforeEach, describe, expect, it } from "vitest";

import { createOidcManager } from "@/lib/oidc-manager";

describe("OIDC transaction storage", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    window.localStorage.clear();
  });

  it("restores redirect state in a new manager on the callback page", async () => {
    const options = {
      authority: "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_test",
      clientId: "test-client",
      redirectUri: "https://peach.example/auth/callback/",
      storage: window.sessionStorage,
    };
    const loginManager = createOidcManager(options);
    await loginManager.settings.stateStore.set("oidc-state", "pending-login");

    const callbackManager = createOidcManager(options);

    await expect(
      callbackManager.settings.stateStore.get("oidc-state"),
    ).resolves.toBe("pending-login");
    expect(callbackManager.settings.stateStore).toBe(
      callbackManager.settings.userStore,
    );
    expect(window.localStorage.length).toBe(0);
  });
});
