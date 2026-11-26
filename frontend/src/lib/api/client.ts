import {
  clearAccessToken,
  getAccessToken,
  setAccessToken,
} from "../auth";

function resolveApiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (configured) return configured.replace(/\\/+$/, "");

  // For LAN development, use the hostname through which the visitor opened
  // the frontend. "localhost" would incorrectly point at the visitor's PC.
  if (typeof window !== "undefined") {
    return `${window.location.protocol}//${window.location.hostname}:8000/api/v1`;
  }

  return "http://localhost:8000/api/v1";
}

export const API_BASE_URL = resolveApiBaseUrl();

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

type RefreshResult = "refreshed" | "expired" | "unavailable";

// All simultaneous 401 responses share one refresh request.
let refreshPromise: Promise<RefreshResult> | null = null;

function notifySessionExpired(): void {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event("dxf2bom:session-expired"));
  }
}

async function refreshAccessToken(): Promise<RefreshResult> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      let response: Response;

      try {
        response = await fetch(`${API_BASE_URL}/auth/refresh`, {
          method: "POST",
          headers: {
            Accept: "application/json",
          },
          credentials: "include",
        });
      } catch {
        // A network failure does not prove that the session expired.
        return "unavailable";
      }

      if (response.status === 401 || response.status === 403) {
        clearAccessToken();
        return "expired";
      }

      if (!response.ok) {
        return "unavailable";
      }

      const data = await response.json().catch(() => null);

      if (typeof data?.access_token !== "string") {
        clearAccessToken();
        return "expired";
      }

      setAccessToken(data.access_token);
      return "refreshed";
    })().finally(() => {
      refreshPromise = null;
    });
  }

  return refreshPromise;
}

async function sendRequest(
  path: string,
  options: RequestInit,
  token: string | null,
): Promise<Response> {
  const headers = new Headers(options.headers);

  headers.set("Accept", "application/json");

  if (
    options.body &&
    !(options.body instanceof FormData) &&
    !headers.has("Content-Type")
  ) {
    headers.set("Content-Type", "application/json");
  }

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  } else {
    headers.delete("Authorization");
  }

  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  try {
    return await fetch(`${API_BASE_URL}${normalizedPath}`, {
      ...options,
      headers,
      credentials: "include",
    });
  } catch {
    throw new ApiError(
      "Cannot connect to the server. Check that the backend is running and try again.",
      0,
    );
  }
}

function getErrorMessage(
  status: number,
  responseData: unknown,
): string {
  const detail =
    typeof responseData === "object" && responseData !== null
      ? (responseData as { detail?: unknown }).detail
      : undefined;

  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  switch (status) {
    case 400:
      return "The request could not be completed. Please check your input.";
    case 401:
      return "Your session has expired. Please sign in again.";
    case 403:
      return "You do not have permission to perform this action.";
    case 404:
      return "The requested information could not be found.";
    case 409:
      return "This operation conflicts with existing data.";
    case 422:
      return "Some information is invalid. Please check your input.";
    case 429:
      return "Too many requests. Please wait a moment and try again.";
    default:
      if (status >= 500) {
        return "The server encountered a problem. Please try again later.";
      }

      return `The request failed (HTTP ${status}). Please try again.`;
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const isAuthEndpoint =
    path.startsWith("/auth/login") ||
    path.startsWith("/auth/register") ||
    path.startsWith("/auth/refresh") ||
    path.startsWith("/auth/logout");

  let token = getAccessToken();

  let response = await sendRequest(path, options, token);

  if (response.status === 401 && !isAuthEndpoint) {
    const refreshResult = await refreshAccessToken();

    if (refreshResult === "expired") {
      if (token) notifySessionExpired();

      throw new ApiError(
        "Your session has expired. Please sign in again.",
        401,
      );
    }

    if (refreshResult === "unavailable") {
      throw new ApiError(
        "We couldn't verify your session right now. Please try again.",
        0,
      );
    }

    token = getAccessToken();
    response = await sendRequest(path, options, token);

    // The refreshed token was rejected too.
    if (response.status === 401) {
      clearAccessToken();
      notifySessionExpired();

      throw new ApiError(
        "Your session has expired. Please sign in again.",
        401,
      );
    }
  }

  const responseData = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(
      getErrorMessage(response.status, responseData),
      response.status,
    );
  }

  return responseData as T;
}