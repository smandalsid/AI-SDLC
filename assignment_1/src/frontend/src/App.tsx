import { lazy, Suspense } from "react";
import { Link, Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./components/AuthProvider";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { RequireAuth } from "./components/RequireAuth";
import { StatusMessage } from "./components/StatusMessage";

const BusListPage = lazy(() =>
  import("./pages/BusListPage").then((module) => ({ default: module.BusListPage })),
);
const BusSeatsPage = lazy(() =>
  import("./pages/BusSeatsPage").then((module) => ({ default: module.BusSeatsPage })),
);

const LoginPage = lazy(() =>
  import("./pages/LoginPage").then((module) => ({ default: module.LoginPage })),
);

function LoginRoute() {
  const { state } = useAuth();
  return state.status === "signedIn" ? <Navigate to="/" replace /> : <LoginPage />;
}

function NotFoundPage() {
  return (
    <main className="page">
      <StatusMessage variant="error" message="Page not found." />
      <Link to="/">Back to all buses</Link>
    </main>
  );
}

export function App() {
  return (
    <ErrorBoundary>
      <Suspense fallback={<StatusMessage variant="loading" message="Loading…" />}>
        <Routes>
          <Route path="/login" element={<LoginRoute />} />
          <Route element={<RequireAuth />}>
            <Route path="/" element={<BusListPage />} />
            <Route path="/buses/:busId" element={<BusSeatsPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </Suspense>
    </ErrorBoundary>
  );
}
