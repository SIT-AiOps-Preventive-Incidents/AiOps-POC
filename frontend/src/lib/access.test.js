// Run with: npm test (node --test, no extra dependencies)
import assert from "node:assert/strict";
import { test } from "node:test";
import { can, groupSpans, matrixChanges, nextPath, toggleCell } from "./access.js";

const me = (role, permissions) => ({ role, permissions });

test("a permission is allowed when the role has it, and an admin has everything", () => {
  assert.equal(can(me("viewer", ["read"]), "read"), true);
  assert.equal(can(me("viewer", ["read"]), "incident.approve"), false);
  assert.equal(can(me("admin", ["admin", "read"]), "anything"), true);
  assert.equal(can(null, "read"), false);
});

test("the header row spans each group over its permissions, in catalog order", () => {
  const perms = [{ id: "admin", group: "Overall" }, { id: "read", group: "Overall" }, { id: "incident.approve", group: "Incidents" }];
  assert.deepEqual(groupSpans(perms, ["Overall", "Incidents", "Demo"]), [{ group: "Overall", span: 2 }, { group: "Incidents", span: 1 }]);
});

test("a cell ticks and unticks, but the admin row and the read column stay on", () => {
  const m = { admin: ["admin", "read"], viewer: ["read"] };
  assert.deepEqual(toggleCell(m, "viewer", "incident.rate").viewer, ["read", "incident.rate"]);
  assert.deepEqual(toggleCell(toggleCell(m, "viewer", "incident.rate"), "viewer", "incident.rate").viewer, ["read"]);
  assert.equal(toggleCell(m, "admin", "read"), m);
  assert.equal(toggleCell(m, "viewer", "read"), m);
  assert.notEqual(toggleCell(m, "viewer", "incident.rate"), m);         // a new object, so Vue sees the change
});

test("unsaved changes list what each role gains and loses", () => {
  const before = { viewer: ["read"], developer: ["read", "fleet.connect"] };
  const after = { viewer: ["read", "incident.rate"], developer: ["read"] };
  assert.deepEqual(matrixChanges(before, after), [
    { role: "viewer", added: ["incident.rate"], removed: [] },
    { role: "developer", added: [], removed: ["fleet.connect"] },
  ]);
  assert.deepEqual(matrixChanges(before, before), []);
});

test("after sign-in we only go back to a page inside the app", () => {
  assert.equal(nextPath("/problems/7"), "/problems/7");
  assert.equal(nextPath("//evil.example"), "/");
  assert.equal(nextPath("https://evil.example"), "/");
  assert.equal(nextPath("/login"), "/");
  assert.equal(nextPath(undefined), "/");
});
