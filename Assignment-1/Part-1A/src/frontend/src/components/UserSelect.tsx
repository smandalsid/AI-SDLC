import { describeApiError } from "../api/errors";
import type { Page, User } from "../api/types";
import type { AsyncResource } from "../hooks/useAsyncResource";
import { StatusMessage } from "./StatusMessage";

interface UserSelectProps {
  users: AsyncResource<Page<User>>;
  value: number | null;
  onChange: (userId: number | null) => void;
}

export function UserSelect({ users, value, onChange }: UserSelectProps) {
  if (users.status === "loading") return <StatusMessage variant="loading" message="Loading users…" />;
  if (users.status === "error") {
    return (
      <StatusMessage variant="error" message={describeApiError(users.error)} onRetry={users.refresh} />
    );
  }
  if (users.data.items.length === 0) return <StatusMessage variant="empty" message="No users available." />;

  return (
    <div className="field">
      <label htmlFor="booking-user">Booking as</label>
      <select
        id="booking-user"
        value={value === null ? "" : String(value)}
        onChange={(event) => onChange(event.target.value === "" ? null : Number(event.target.value))}
      >
        <option value="">Choose a user</option>
        {users.data.items.map((user) => (
          <option key={user.id} value={user.id}>
            {user.name}
          </option>
        ))}
      </select>
    </div>
  );
}
