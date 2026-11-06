import js from "@eslint/js";
import { defineConfig, globalIgnores } from "eslint/config";
import reactHooks from "eslint-plugin-react-hooks";
import tseslint from "typescript-eslint";

// Exported by .harness/lint.sh from thresholds.env; there is deliberately no fallback number.
const maxFunctionLines = Number(process.env.FUNCTION_MAX_LINES);
if (!Number.isInteger(maxFunctionLines) || maxFunctionLines <= 0) {
  throw new Error("FUNCTION_MAX_LINES is not set; run ESLint through .harness/lint.sh");
}

export default defineConfig([
  globalIgnores(["dist", "coverage", "playwright-report", "test-results"]),
  {
    files: ["**/*.{ts,tsx}"],
    extends: [js.configs.recommended, tseslint.configs.strict, reactHooks.configs.flat.recommended],
    rules: {
      "@typescript-eslint/no-explicit-any": "error",
    },
  },
  {
    files: ["src/**/*.{ts,tsx}"],
    rules: {
      "max-lines-per-function": [
        "error",
        { max: maxFunctionLines, skipBlankLines: true, skipComments: true },
      ],
    },
  },
  {
    files: ["src/components/**/*.{ts,tsx}", "src/pages/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-globals": [
        "error",
        { name: "fetch", message: "Call the API through src/api via a hook, not directly." },
      ],
    },
  },
]);
