/// <reference types="node" />
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const RESET_SCRIPT = fileURLToPath(new URL("../../../scripts/e2e-reset.sh", import.meta.url));

/** Returns the test database to the seeded state (3 buses, 3 users, no bookings). */
export function resetDatabase(): void {
  execFileSync(RESET_SCRIPT, { stdio: "pipe" });
}
