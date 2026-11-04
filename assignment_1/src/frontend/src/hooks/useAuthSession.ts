import { useCallback, useMemo, useState } from "react";
import { login } from "../api/auth";
import { clearToken, setToken } from "../api/session";
import type { AuthUser } from "../api/types";

export type AuthState = { status: "signedOut" } | { status: "signedIn"; user: AuthUser };

export interface AuthSession {
  state: AuthState;
  signIn: (username: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const SIGNED_OUT: AuthState = { status: "signedOut" };

export function useAuthSession(): AuthSession {
  const [state, setState] = useState<AuthState>(SIGNED_OUT);

  const signIn = useCallback(async (username: string, password: string) => {
    const response = await login(username, password);
    // The token is stored only after the server accepted the credentials; the name comes from it too.
    setToken(response.access_token);
    setState({ status: "signedIn", user: response.user });
  }, []);

  const signOut = useCallback(() => {
    clearToken();
    setState(SIGNED_OUT);
    return Promise.resolve();
  }, []);

  return useMemo(() => ({ state, signIn, signOut }), [state, signIn, signOut]);
}
