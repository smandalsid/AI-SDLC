import { describeApiError } from "../api/errors";
import { BusList } from "../components/BusList";
import { StatusMessage } from "../components/StatusMessage";
import { useBuses } from "../hooks/useBuses";

export function BusListPage() {
  const buses = useBuses();

  return (
    <main className="page">
      <h1>Buses</h1>
      {buses.status === "loading" && <StatusMessage variant="loading" message="Loading buses…" />}
      {buses.status === "error" && (
        <StatusMessage
          variant="error"
          message={describeApiError(buses.error)}
          onRetry={buses.refresh}
        />
      )}
      {buses.status === "ready" &&
        (buses.data.items.length === 0 ? (
          <StatusMessage variant="empty" message="No buses available." />
        ) : (
          <BusList buses={buses.data.items} />
        ))}
    </main>
  );
}
