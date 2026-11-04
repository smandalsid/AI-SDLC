import { useCallback } from "react";
import { getBus } from "../api/buses";
import type { BusDetail } from "../api/types";
import { useAsyncResource, type AsyncResource } from "./useAsyncResource";

export function useBusDetail(busId: number): AsyncResource<BusDetail> {
  const load = useCallback(() => getBus(busId), [busId]);
  return useAsyncResource(load);
}
