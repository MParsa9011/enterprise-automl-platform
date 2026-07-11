import axios, { AxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from "axios";

import type { ApiErrorBody, Tokens } from "@/types/api";
import { tokenStore } from "@/lib/tokenStore";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

export const api: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
});

// Attach the access token to every outgoing request.
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = tokenStore.getAccess();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// --- Transparent refresh-token rotation -----------------------------------
// On a 401 we attempt a single refresh and replay the original request. A
// module-level promise de-duplicates concurrent refreshes so a burst of 401s
// only triggers one refresh call.
let refreshPromise: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  const refreshToken = tokenStore.getRefresh();
  if (!refreshToken) {
    throw new Error("No refresh token");
  }
  const { data } = await axios.post<Tokens>(`${BASE_URL}/auth/refresh`, {
    refresh_token: refreshToken,
  });
  tokenStore.set(data);
  return data.access_token;
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiErrorBody>) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined;
    const isAuthCall = original?.url?.includes("/auth/");

    if (error.response?.status === 401 && original && !original._retried && !isAuthCall) {
      original._retried = true;
      try {
        refreshPromise = refreshPromise ?? refreshAccessToken();
        const newToken = await refreshPromise;
        refreshPromise = null;
        original.headers.Authorization = `Bearer ${newToken}`;
        return api(original);
      } catch (refreshError) {
        refreshPromise = null;
        tokenStore.clear();
        return Promise.reject(refreshError);
      }
    }
    return Promise.reject(error);
  },
);

/** Extract a human-readable message from an Axios error's API envelope. */
export function apiErrorMessage(error: unknown, fallback = "Something went wrong"): string {
  if (axios.isAxiosError<ApiErrorBody>(error)) {
    return error.response?.data?.error?.message ?? error.message ?? fallback;
  }
  return error instanceof Error ? error.message : fallback;
}
