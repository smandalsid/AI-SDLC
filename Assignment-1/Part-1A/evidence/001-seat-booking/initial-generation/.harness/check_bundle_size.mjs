// Fails when the initial JS (entry script plus modulepreload chunks) exceeds BUNDLE_MAX_KB_GZIP, gzipped.
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { gzipSync } from "node:zlib";

const limitKb = Number(process.env.BUNDLE_MAX_KB_GZIP);
if (!Number.isFinite(limitKb) || limitKb <= 0) {
  console.error("BUNDLE_MAX_KB_GZIP is not set; run through .harness/build.sh");
  process.exit(2);
}

const dist = path.resolve("src/frontend/dist");
const indexPath = path.join(dist, "index.html");
if (!existsSync(indexPath)) {
  console.error(`missing ${indexPath}; run the build first`);
  process.exit(2);
}

const html = readFileSync(indexPath, "utf8");
const refs = new Set();
for (const match of html.matchAll(/<script[^>]*\ssrc="([^"]+\.js)"/g)) refs.add(match[1]);
for (const match of html.matchAll(/<link[^>]*rel="modulepreload"[^>]*href="([^"]+\.js)"/g)) {
  refs.add(match[1]);
}

let totalBytes = 0;
for (const ref of refs) {
  const file = path.join(dist, ref.replace(/^\//, ""));
  const gzipped = gzipSync(readFileSync(file)).length;
  totalBytes += gzipped;
  console.log(`${ref}: ${(gzipped / 1024).toFixed(1)} KB gzipped`);
}

const totalKb = totalBytes / 1024;
console.log(`initial JS total: ${totalKb.toFixed(1)} KB gzipped (limit ${limitKb} KB)`);
if (refs.size === 0 || totalKb > limitKb) {
  console.error(refs.size === 0 ? "no initial JS found in index.html" : "bundle size budget exceeded");
  process.exit(1);
}
