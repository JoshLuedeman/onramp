import type { IPublicClientApplication, EventMessage } from "@azure/msal-browser";

const clientId = import.meta.env.VITE_AZURE_CLIENT_ID || "";

if (!clientId) {
  console.info("MSAL not configured — running without authentication");
}

let msalInstance: IPublicClientApplication | null = null;

async function initMsal() {
  if (!clientId || msalInstance) return msalInstance;
  const { PublicClientApplication, EventType } = await import("@azure/msal-browser");
  const { msalConfig } = await import("./msalConfig");
  msalInstance = new PublicClientApplication(msalConfig);
  await msalInstance.initialize();
  const accounts = msalInstance.getAllAccounts();
  if (accounts.length > 0) {
    msalInstance.setActiveAccount(accounts[0]);
  }
  msalInstance.addEventCallback((event: EventMessage) => {
    if (event.eventType === EventType.LOGIN_SUCCESS && event.payload) {
      const payload = event.payload as { account?: Parameters<IPublicClientApplication["setActiveAccount"]>[0] };
      if (payload.account) {
        msalInstance!.setActiveAccount(payload.account);
      }
    }
  });
  return msalInstance;
}

export { msalInstance, initMsal };
