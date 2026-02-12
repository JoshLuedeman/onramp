const clientId = import.meta.env.VITE_AZURE_CLIENT_ID || "";

export function useAuth() {
  // Dev mode — no MSAL, return mock auth state
  if (!clientId) {
    return {
      isAuthenticated: false,
      user: null,
      login: async () => { console.info("Auth not configured in dev mode"); },
      logout: async () => {},
      getAccessToken: async () => null,
    };
  }

  // Production mode — use MSAL
  const { useMsal, useIsAuthenticated } = require("@azure/msal-react");
  const { loginRequest } = require("./msalConfig");
  const { instance, accounts } = useMsal();
  const isAuthenticated = useIsAuthenticated();

  const login = async () => {
    try {
      await instance.loginPopup(loginRequest);
    } catch (error) {
      console.error("Login failed:", error);
    }
  };

  const logout = async () => {
    try {
      await instance.logoutPopup();
    } catch (error) {
      console.error("Logout failed:", error);
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
    } catch (error) {
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
