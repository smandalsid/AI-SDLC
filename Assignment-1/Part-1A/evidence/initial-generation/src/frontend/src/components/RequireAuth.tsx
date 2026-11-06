import { Navigate, Outlet } from "react-router-dom";
import { describeApiError } from "../api/errors";
import { AppHeader } from "./AppHeader";
import { useAuth } from "./AuthProvider";
import { StatusMessage } from "./StatusMessage";

/** Renders the nested route only once the server has confirmed the session. */
export function RequireAuth() {
  const { state } = useAuth();

  if (state.status === "checking") {
    return <StatusMessage variant="loading" message="Checking your session…" />;
  }
  if (state.status === "unavailable") {
    return <StatusMessage variant="error" message={describeApiError(null)} />;
  }
  if (state.status === "signedOut") return <Navigate to="/login" replace />;
  return (
    <>
      <AppHeader />
      <Outlet />
    </>
  );
}
