import { describe, expect, it } from "vitest";

const sources = import.meta.glob<string>("../src/{components,pages}/**/*.{ts,tsx}", {
  query: "?raw",
  import: "default",
  eager: true,
});

describe("architecture: components and pages never call the network directly", () => {
  it("scans the component and page sources", () => {
    const paths = Object.keys(sources);

    expect(paths.some((path) => path.includes("/components/"))).toBe(true);
    expect(paths.some((path) => path.includes("/pages/"))).toBe(true);
  });

  it("contains no fetch call in src/components or src/pages", () => {
    const offenders = Object.entries(sources)
      .filter(([, source]) => /\bfetch\b/.test(source))
      .map(([path]) => path);

    expect(offenders).toEqual([]);
  });
});
