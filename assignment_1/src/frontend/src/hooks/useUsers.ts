import { listUsers } from "../api/users";
import type { Page, User } from "../api/types";
import { useAsyncResource, type AsyncResource } from "./useAsyncResource";

export function useUsers(): AsyncResource<Page<User>> {
  return useAsyncResource(listUsers);
}
