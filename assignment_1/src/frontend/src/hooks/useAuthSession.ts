import { useCallback, useEffect, useMemo, useState } from "react";
import { login, logout, me } from "../api/auth";
import { ApiError } from "../api/errors";
import { clearToken, getToken, setToken, subscribe } from "../api/session";
import type { AuthUser } from "../api/types";

export type AuthState =
  | { status: "checking" }
  | { status: "unavailable" }
  | { status: "signedOut" }
  | { status: "signedIn"; user: AuthUser };

export interface AuthSession {
  state: AuthState;
  signIn: (username: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const SIGNED_OUT: AuthState = { status: "signedOut" };

function initialState(): AuthState {
  return getToken() === null ? SIGNED_OUT : { status: "checking" };
}

export function useAuthSession(): AuthSession {
  const [state, setState] = useState<AuthState>(initialState);

  useEffect(() => subscribe(() => setState(SIGNED_OUT)), []);

  useEffect(() => {
    if (state.status !== "checking") return;
    let cancelled = false;
    me().then(
      (user) => {
        if (!cancelled) setState({ status: "signedIn", user });
      },
      (error: unknown) => {
        if (cancelled) return;
        if (error instanceof ApiError && error.kind === "unauthenticated") {
          clearToken();
          setState(SIGNED_OUT);
        } else {
          // The token may still be good; keep it and let the user retry by reloading.
          setState({ status: "unavailable" });
        }
      },
    );
    return () => {
      cancelled = true;
    };
  }, [state.status]);

  const signIn = useCallback(async (username: string, password: string) => {
    const response = await login(username, password);
    // The token is stored only after the server accepted the credentials; the name comes from it too.
    setToken(response.access_token);
    setState({ status: "signedIn", user: response.user });
  }, []);

  const signOut = useCallback(async () => {
    try {
      // The server call needs the token, so it goes first.
      await logout();
    } catch {
      // A failed call must never keep the user signed in on this screen.
    } finally {
      clearToken();
      setState(SIGNED_OUT);
    }
  }, []);

  return useMemo(() => ({ state, signIn, signOut }), [state, signIn, signOut]);
}
