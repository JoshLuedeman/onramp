import { useMsal, useIsAuthenticated } from "@azure/msal-react";
import { loginRequest } from "./msalConfig";

const clientId = import.meta.env.VITE_AZURE_CLIENT_ID || "";

function useMsalAuth() {
  const { instance, accounts } = useMsal();
  const isAuthenticated = useIsAuthenticated();

  const login = async () => {
    try {
      await instance.loginPopup(loginRequest);
    } catch (err) {
      console.error("Login failed:", err);
    }
  };

  const logout = async () => {
    try {
      await instance.logoutPopup();
    } catch (err) {
      console.error("Logout failed:", err);
    }
  };

  const getAccessToken = async (): Promise<string | null> => {
    if (accounts.length === 0) return null;
    try {
      const response = await instance.acquireTokenSilent({
        ...loginRequest,
        account: accounts[0],
      });
      return response.accessToken;
    } catch {
      try {
        const response = await instance.acquireTokenPopup(loginRequest);
        return response.accessToken;
      } catch (popupError) {
        console.error("Token acquisition failed:", popupError);
        return null;
      }
    }
  };

  const user = accounts.length > 0 ? {
    name: accounts[0].name || "",
    email: accounts[0].username || "",
    id: accounts[0].localAccountId,
  } : null;

  return { isAuthenticated, user, login, logout, getAccessToken };
}

const devAuth = {
  isAuthenticated: false,
  user: null,
  login: async () => { console.info("Auth not configured in dev mode"); },
  logout: async () => {},
  getAccessToken: async () => null,
};

export function useAuth() {
  const msalAuth = useMsalAuth();
  if (!clientId) {
    return devAuth;
  }
  return msalAuth;
}
