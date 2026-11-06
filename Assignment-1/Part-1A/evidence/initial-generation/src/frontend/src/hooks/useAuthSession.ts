import { useCallback, useEffect, useMemo, useState } from "react";
import { login, logout, me } from "../api/auth";
import { ApiError } from "../api/errors";
import { clearToken, getToken, setToken, subscribe } from "../api/session";
import type { AuthUser } from "../api/types";

export type SignedOutReason = "none" | "signedOut" | "expired";

export type AuthState =
  | { status: "checking" }
  | { status: "unavailable" }
  | { status: "signedOut"; reason: SignedOutReason }
  | { status: "signedIn"; user: AuthUser };

export interface AuthSession {
  state: AuthState;
  signIn: (username: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const signedOutBecause = (reason: SignedOutReason): AuthState => ({ status: "signedOut", reason });

function initialState(): AuthState {
  return getToken() === null ? signedOutBecause("none") : { status: "checking" };
}

type SetState = (state: AuthState) => void;

/** Asks the server who the stored token belongs to, once, while the state is `checking`. */
function useSessionCheck(status: AuthState["status"], setState: SetState): void {
  useEffect(() => {
    if (status !== "checking") return;
    let cancelled = false;
    me().then(
      (user) => {
        if (!cancelled) setState({ status: "signedIn", user });
      },
      (error: unknown) => {
        if (cancelled) return;
        if (error instanceof ApiError && error.kind === "unauthenticated") {
          clearToken();
          setState(signedOutBecause("expired"));
        } else {
          // The token may still be good; keep it and let the user retry by reloading.
          setState({ status: "unavailable" });
        }
      },
    );
    return () => {
      cancelled = true;
    };
  }, [status, setState]);
}

export function useAuthSession(): AuthSession {
  const [state, setState] = useState<AuthState>(initialState);

  useEffect(() => subscribe(() => setState(signedOutBecause("expired"))), []);

  useSessionCheck(state.status, setState);

  const signIn = useCallback(async (username: string, password: string) => {
    // Any new attempt retires the expiry message.
    setState(signedOutBecause("none"));
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
      setState(signedOutBecause("signedOut"));
    }
  }, []);

  return useMemo(() => ({ state, signIn, signOut }), [state, signIn, signOut]);
}
