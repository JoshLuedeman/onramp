import { useState, useEffect, type ReactNode } from "react";
import type { IPublicClientApplication } from "@azure/msal-browser";
import { msalInstance } from "./msalInstance";

const clientId = import.meta.env.VITE_AZURE_CLIENT_ID || "";

interface AuthProviderProps {
  children: ReactNode;
}

export default function AuthProvider({ children }: AuthProviderProps) {
  const [MsalProvider, setMsalProvider] = useState<React.ComponentType<{ instance: IPublicClientApplication; children: ReactNode }> | null>(null);

  useEffect(() => {
    if (clientId) {
      import("@azure/msal-react").then((mod) => setMsalProvider(() => mod.MsalProvider));
    }
  }, []);

  if (!clientId) {
    return <>{children}</>;
  }

  if (!MsalProvider || !msalInstance) {
    return <>{children}</>;
  }

  return <MsalProvider instance={msalInstance}>{children}</MsalProvider>;
}
