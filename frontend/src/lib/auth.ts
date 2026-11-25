const ACCESS_TOKEN_KEY = "dxf2bom_access_token";

/**
 * Read the access token for the current browser session.
 */
export function getAccessToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  return sessionStorage.getItem(ACCESS_TOKEN_KEY);
}

/**
 * Save the access token for the current browser session.
 */
export function setAccessToken(token: string): void {
  if (typeof window === "undefined") {
    return;
  }

  sessionStorage.setItem(ACCESS_TOKEN_KEY, token);
}

/**
 * Remove the access token.
 */
export function clearAccessToken(): void {
  if (typeof window === "undefined") {
    return;
  }

  sessionStorage.removeItem(ACCESS_TOKEN_KEY);
}

/**
 * Check whether an access token exists.
 */
export function hasAccessToken(): boolean {
  return getAccessToken() !== null;
}