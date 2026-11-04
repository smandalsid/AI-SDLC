import { request } from "./client";
import type { Bus, BusDetail, Page } from "./types";

export function listBuses(): Promise<Page<Bus>> {
  return request<Page<Bus>>("/buses");
}

export function getBus(busId: number): Promise<BusDetail> {
  return request<BusDetail>(`/buses/${busId}`);
}
