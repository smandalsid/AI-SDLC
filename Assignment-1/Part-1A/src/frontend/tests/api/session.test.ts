import { afterEach, describe, expect, it, vi } from "vitest";
import { clearToken, expire, getToken, setToken, subscribe } from "../../src/api/session";

afterEach(() => {
  vi.restoreAllMocks();
  clearToken();
});

describe("session store", () => {
  it("has no token at first", () => {
    expect(getToken()).toBeNull();
  });

  it("keeps only the token, in sessionStorage under one key", () => {
    setToken("token-value");

    expect(getToken()).toBe("token-value");
    expect(sessionStorage.length).toBe(1);
    const key = sessionStorage.key(0);
    expect(sessionStorage.getItem(key ?? "")).toBe("token-value");
    expect(localStorage.length).toBe(0);
  });

  it("clears the token", () => {
    setToken("token-value");

    clearToken();

    expect(getToken()).toBeNull();
    expect(sessionStorage.length).toBe(0);
  });

  it("expire() clears the token and tells every subscriber once", () => {
    const first = vi.fn();
    const second = vi.fn();
    subscribe(first);
    subscribe(second);
    setToken("token-value");

    expire();

    expect(getToken()).toBeNull();
    expect(first).toHaveBeenCalledTimes(1);
    expect(second).toHaveBeenCalledTimes(1);
  });

  it("expire() says nothing when no token is stored, so a late 401 after sign-out is not an expiry", () => {
    const listener = vi.fn();
    const unsubscribe = subscribe(listener);

    expire();

    expect(listener).not.toHaveBeenCalled();
    unsubscribe();
  });

  it("stops notifying a subscriber that unsubscribed", () => {
    const listener = vi.fn();
    const unsubscribe = subscribe(listener);

    unsubscribe();
    setToken("token-value");
    expire();

    expect(listener).not.toHaveBeenCalled();
  });

  it("treats unavailable storage as no token and never throws", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("denied", "SecurityError");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("denied", "SecurityError");
    });
    vi.spyOn(Storage.prototype, "removeItem").mockImplementation(() => {
      throw new DOMException("denied", "SecurityError");
    });

    expect(getToken()).toBeNull();
    expect(() => setToken("token-value")).not.toThrow();
    expect(() => clearToken()).not.toThrow();
    expect(() => expire()).not.toThrow();
  });
});
