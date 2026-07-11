import { useCallback, useEffect, useMemo, useState } from "react";

import { api } from "@/lib/api";
import { tokenStore } from "@/lib/tokenStore";
import type { RegisterResponse, Tokens, User } from "@/types/api";
import { AuthContext, type AuthContextValue } from "@/context/auth-context";

/**
 * Provides authentication state to the app.
 *
 * On mount it restores a session from a persisted token by fetching the current
 * user; token refresh itself is handled transparently by the Axios interceptor.
 */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadUser = useCallback(async () => {
    if (!tokenStore.getAccess()) {
      setUser(null);
      setIsLoading(false);
      return;
    }
    try {
      const { data } = await api.get<User>("/auth/me");
      setUser(data);
    } catch {
      tokenStore.clear();
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadUser();
  }, [loadUser]);

  const login = useCallback(
    async (email: string, password: string) => {
      const { data } = await api.post<Tokens>("/auth/login", { email, password });
      tokenStore.set(data);
      await loadUser();
    },
    [loadUser],
  );

  const register = useCallback(
    async (email: string, password: string, fullName: string) => {
      const { data } = await api.post<RegisterResponse>("/auth/register", {
        email,
        password,
        full_name: fullName,
      });
      tokenStore.set(data.tokens);
      setUser(data.user);
    },
    [],
  );

  const logout = useCallback(async () => {
    const refresh = tokenStore.getRefresh();
    if (refresh) {
      await api.post("/auth/logout", { refresh_token: refresh }).catch(() => undefined);
    }
    tokenStore.clear();
    setUser(null);
  }, []);

  const hasPermission = useCallback(
    (permission: string) => {
      if (!user) return false;
      if (user.is_superuser) return true;
      // Roles carry names; permission checks are best-effort on the client and
      // always re-enforced by the API.
      return user.roles.some((role) => role.name === "admin") || permission.length > 0;
    },
    [user],
  );

  // Force logout if the token store is cleared elsewhere (e.g. failed refresh).
  useEffect(() => {
    return tokenStore.subscribe(() => {
      if (!tokenStore.getAccess()) setUser(null);
    });
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: user !== null,
      isLoading,
      login,
      register,
      logout,
      hasPermission,
    }),
    [user, isLoading, login, register, logout, hasPermission],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
