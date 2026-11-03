import { listBuses } from "../api/buses";
import type { Bus, Page } from "../api/types";
import { useAsyncResource, type AsyncResource } from "./useAsyncResource";

export function useBuses(): AsyncResource<Page<Bus>> {
  return useAsyncResource(listBuses);
}
