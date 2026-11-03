import { request } from "./client";
import type { Page, User } from "./types";

export function listUsers(): Promise<Page<User>> {
  return request<Page<User>>("/users");
}
