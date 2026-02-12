import type { ReactNode } from "react";

const clientId = import.meta.env.VITE_AZURE_CLIENT_ID || "";

interface AuthProviderProps {
  children: ReactNode;
}

// When no client ID is configured, skip MSAL entirely (dev mode)
if (!clientId) {
  console.info("MSAL not configured — running without authentication");
}

let msalInstance: any = null;

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
  msalInstance.addEventCallback((event: any) => {
    if (event.eventType === EventType.LOGIN_SUCCESS && event.payload) {
      msalInstance.setActiveAccount(event.payload.account);
    }
  });
  return msalInstance;
}

export default function AuthProvider({ children }: AuthProviderProps) {
  if (!clientId) {
    // No auth configured — render children directly
    return <>{children}</>;
  }

  // Dynamic import for MsalProvider when auth is configured
  const { MsalProvider } = require("@azure/msal-react");
  return <MsalProvider instance={msalInstance}>{children}</MsalProvider>;
}

export { msalInstance, initMsal };
