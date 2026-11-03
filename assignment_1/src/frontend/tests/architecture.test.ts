import { describe, expect, it } from "vitest";

const sources = import.meta.glob<string>("../src/{components,pages,hooks}/**/*.{ts,tsx}", {
  query: "?raw",
  import: "default",
  eager: true,
});

const allSources = import.meta.glob<string>("../src/**/*.{ts,tsx}", {
  query: "?raw",
  import: "default",
  eager: true,
});

const SESSION_MODULE = "../src/api/session.ts";

describe("architecture: components, pages, and hooks never call the network directly", () => {
  it("scans the component, page, and hook sources", () => {
    const paths = Object.keys(sources);

    expect(paths.some((path) => path.includes("/components/"))).toBe(true);
    expect(paths.some((path) => path.includes("/pages/"))).toBe(true);
    expect(paths.some((path) => path.includes("/hooks/"))).toBe(true);
  });

  it("contains no fetch call in src/components, src/pages, or src/hooks", () => {
    const offenders = Object.entries(sources)
      .filter(([, source]) => /\bfetch\b/.test(source))
      .map(([path]) => path);

    expect(offenders).toEqual([]);
  });
});

describe("architecture: only the session store touches browser storage", () => {
  it("has the session store module", () => {
    expect(Object.keys(allSources)).toContain(SESSION_MODULE);
  });

  it("contains no sessionStorage or localStorage access outside src/api/session.ts", () => {
    const offenders = Object.entries(allSources)
      .filter(([path]) => path !== SESSION_MODULE)
      .filter(([, source]) => /\b(sessionStorage|localStorage)\b/.test(source))
      .map(([path]) => path);

    expect(offenders).toEqual([]);
  });

  it("never uses localStorage, even in the session store", () => {
    expect(allSources[SESSION_MODULE] ?? "").not.toMatch(/\blocalStorage\b/);
  });
});
