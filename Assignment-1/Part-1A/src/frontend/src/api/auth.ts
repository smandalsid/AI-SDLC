import { request } from "./client";
import type { AuthUser, LoginResponse } from "./types";

export function login(username: string, password: string): Promise<LoginResponse> {
  return request<LoginResponse>("/auth/login", { method: "POST", body: { username, password } });
}

export function me(): Promise<AuthUser> {
  return request<AuthUser>("/auth/me");
}
