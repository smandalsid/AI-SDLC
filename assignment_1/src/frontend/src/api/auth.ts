import { request } from "./client";
import type { AuthUser, LoginResponse } from "./types";

export function login(username: string, password: string): Promise<LoginResponse> {
  return request<LoginResponse>("/auth/login", { method: "POST", body: { username, password } });
}

export function logout(): Promise<undefined> {
  return request<undefined>("/auth/logout", { method: "POST" });
}

export function me(): Promise<AuthUser> {
  return request<AuthUser>("/auth/me");
}
