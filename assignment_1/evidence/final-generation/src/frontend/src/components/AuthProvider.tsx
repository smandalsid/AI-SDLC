import { createContext, useContext, type ReactNode } from "react";
import { useAuthSession, type AuthSession } from "../hooks/useAuthSession";

export const AuthContext = createContext<AuthSession | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const session = useAuthSession();
  return <AuthContext.Provider value={session}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthSession {
  const session = useContext(AuthContext);
  if (session === null) throw new Error("useAuth must be used inside an AuthProvider");
  return session;
}
