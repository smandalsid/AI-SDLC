import { Link } from "react-router-dom";
import type { Bus } from "../api/types";

export function BusList({ buses }: { buses: Bus[] }) {
  return (
    <ul className="bus-list">
      {buses.map((bus) => (
        <li key={bus.id}>
          <Link to={`/buses/${bus.id}`}>
            {bus.name} <span>{bus.total_seats} seats</span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
