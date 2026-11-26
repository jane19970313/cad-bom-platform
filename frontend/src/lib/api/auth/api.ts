import {
  apiRequest,
  ApiError,
  API_BASE_URL,
} from "../client";

import {
  clearAccessToken,
  setAccessToken,
} from "@/lib/auth";

import type {
  TokenResponse,
  RegisterRequest,
  UserResponse,
} from "@/types/auth";

// Register
export async function register(
  payload: RegisterRequest,
): Promise<UserResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    credentials: "include",
    body: JSON.stringify({
      email: payload.email.trim().toLowerCase(),
      password: payload.password,
    }),
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const message =
      typeof data?.detail === "string"
        ? data.detail
        : "Registration failed.";

    throw new ApiError(message, response.status);
  }

  return data as UserResponse;
}

// Login
export async function login(
  email: string,
  password: string,
): Promise<TokenResponse> {
  const formData = new URLSearchParams();

  formData.set("username", email.trim().toLowerCase());
  formData.set("password", password);

  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      Accept: "application/json",
    },
    credentials: "include",
    body: formData.toString(),
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const message =
      typeof data?.detail === "string"
        ? data.detail
        : "Login failed.";

    throw new ApiError(message, response.status);
  }

  const token = data as TokenResponse;

  if (!token.access_token) {
    throw new ApiError(
      "The server did not return an access token.",
      response.status,
    );
  }

  setAccessToken(token.access_token);
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event("dxf2bom:auth-changed"));
  }

  return token;
}

// Logout
export async function logout(): Promise<void> {
  try {
    await fetch(`${API_BASE_URL}/auth/logout`, {
      method: "POST",
      headers: {
        Accept: "application/json",
      },
      credentials: "include",
    });
  } finally {
    clearAccessToken();
    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event("dxf2bom:auth-changed"));
    }
  }
}

// Get current user
export async function getCurrentUser<T>(): Promise<T> {
  return apiRequest<T>("/auth/me");
}