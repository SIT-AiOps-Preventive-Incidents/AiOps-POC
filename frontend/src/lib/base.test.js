import assert from "node:assert/strict";
import { test } from "node:test";
import { at, basePath } from "./base.js";

test("the app's own folder is the page path up to the last slash", () => {
  assert.equal(basePath("/"), "/");
  assert.equal(basePath("/index.html"), "/");
  assert.equal(basePath("/capstone26/cp26pt1/"), "/capstone26/cp26pt1/");
  assert.equal(basePath("/capstone26/cp26pt1/index.html"), "/capstone26/cp26pt1/");
});

test("an address inside the app is put under that folder, so a proxy with a path in front works", () => {
  assert.equal(at("/api/v1/auth/me", "/"), "/api/v1/auth/me");
  assert.equal(at("/api/v1/auth/me", "/capstone26/cp26pt1/"), "/capstone26/cp26pt1/api/v1/auth/me");
  assert.equal(at("icons/f/home.svg", "/capstone26/cp26pt1/"), "/capstone26/cp26pt1/icons/f/home.svg");
});
