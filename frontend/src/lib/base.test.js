import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";
import { at, basePath } from "./base.js";

const PUB = "/capstone26/cp26pt1/";

test("the app's own folder is the page path up to the last slash", () => {
  assert.equal(basePath("/"), "/");
  assert.equal(basePath("/index.html"), "/");
  assert.equal(basePath(PUB), PUB);
  assert.equal(basePath(PUB + "index.html"), PUB);
});

test("a path that looks like another host stays on this one", () => {
  assert.equal(basePath("//evil.example/"), "/evil.example/");
  assert.equal(basePath("///evil.example//x"), "/evil.example/");
  assert.equal(basePath(""), "/");
});

test("the query string and the hash of the page are not part of the folder", () => {
  const u = new URL("https://public.example/capstone26/cp26pt1/?theme=dark&next=/a/b#/problems?status=open");
  assert.equal(basePath(u.pathname), PUB);
});

test("an address inside the app is put under that folder", () => {
  assert.equal(at("/api/v1/auth/me", "/"), "/api/v1/auth/me");
  assert.equal(at("api/v1/auth/me", PUB), "/capstone26/cp26pt1/api/v1/auth/me");
  assert.equal(at("//api/v1", PUB), "/capstone26/cp26pt1/api/v1");
  assert.equal(at("icons/f/home.svg", PUB), "/capstone26/cp26pt1/icons/f/home.svg");
});

test("a query string is kept as it is", () => {
  assert.equal(at("api/v1/incidents?status=open&limit=5", PUB), "/capstone26/cp26pt1/api/v1/incidents?status=open&limit=5");
  assert.equal(at("api/v1/services/a%2Fb?x=%20", PUB), "/capstone26/cp26pt1/api/v1/services/a%2Fb?x=%20");
});

test("no page asks for a file or a call from the root of the site", () => {
  const src = fileURLToPath(new URL("..", import.meta.url));
  const bad = [];
  (function walk(dir) {
    for (const f of fs.readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, f.name);
      if (f.isDirectory()) { walk(p); continue; }
      if (!/\.(vue|js|css)$/.test(f.name) || f.name.endsWith(".test.js")) continue;
      fs.readFileSync(p, "utf8").split("\n").forEach((line, i) => {
        if (/^\s*(\/\/|\*)/.test(line)) return;
        if (/["'`(]\/(api|icons|assets|install|docs|favicon)\b/.test(line)) bad.push(`${path.relative(src, p)}:${i + 1}`);
      });
    }
  })(src);
  assert.deepEqual(bad, []);
});
