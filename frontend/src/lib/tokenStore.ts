import type { Tokens } from "@/types/api";

/**
 * Persists the JWT token pair in localStorage.
 *
 * A tiny event emitter lets the auth context react to token changes (e.g. a
 * forced logout triggered by a failed refresh in the Axios interceptor).
 */
const ACCESS_KEY = "automl.access_token";
const REFRESH_KEY = "automl.refresh_token";

type Listener = () => void;
const listeners = new Set<Listener>();

export const tokenStore = {
  getAccess(): string | null {
    return localStorage.getItem(ACCESS_KEY);
  },
  getRefresh(): string | null {
    return localStorage.getItem(REFRESH_KEY);
  },
  set(tokens: Pick<Tokens, "access_token" | "refresh_token">): void {
    localStorage.setItem(ACCESS_KEY, tokens.access_token);
    localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
    listeners.forEach((listener) => listener());
  },
  clear(): void {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    listeners.forEach((listener) => listener());
  },
  subscribe(listener: Listener): () => void {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },
};
