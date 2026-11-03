import { resetDatabase } from "./support";

export default function globalSetup(): void {
  resetDatabase();
}
