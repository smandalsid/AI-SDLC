const STORAGE_KEY = "bus-booking.session-token";

type Listener = () => void;

const listeners = new Set<Listener>();

// Only the token is stored (per tab); a blocked or unavailable storage simply means "no session".
export function getToken(): string | null {
  try {
    return sessionStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string): void {
  try {
    sessionStorage.setItem(STORAGE_KEY, token);
  } catch {
    // Without storage the session lasts only until the page is left.
  }
}

export function clearToken(): void {
  try {
    sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // Nothing stored, nothing to clear.
  }
}

export function subscribe(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** The server no longer accepts the token: forget it and tell the app. */
export function expire(): void {
  // No token means the user already signed out; a late 401 is not an expiry.
  if (getToken() === null) return;
  clearToken();
  for (const listener of [...listeners]) listener();
}
