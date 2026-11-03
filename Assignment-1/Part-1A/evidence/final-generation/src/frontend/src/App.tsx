import { lazy, Suspense } from "react";
import { Link, Route, Routes } from "react-router-dom";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { StatusMessage } from "./components/StatusMessage";

const BusListPage = lazy(() =>
  import("./pages/BusListPage").then((module) => ({ default: module.BusListPage })),
);
const BusSeatsPage = lazy(() =>
  import("./pages/BusSeatsPage").then((module) => ({ default: module.BusSeatsPage })),
);

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
          <Route path="/" element={<BusListPage />} />
          <Route path="/buses/:busId" element={<BusSeatsPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Suspense>
    </ErrorBoundary>
  );
}
