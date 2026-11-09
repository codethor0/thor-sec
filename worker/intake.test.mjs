// Unit tests for worker/intake.mjs. Run: node --test worker/
import test from "node:test";
import assert from "node:assert/strict";
import worker, { handleIntake, readBody, SUCCESS_URL, MAX_BODY_BYTES } from "./intake.mjs";

const ORIGIN = "https://codethor0.github.io";
const VALID = {
  name: "Test Person",
  email: "test@example.org",
  organization: "Example Org",
  question: "Assess agent tool-call authorization boundaries.",
  objective: "Internal hardening",
  scope: "Staging only",
  authorization: "owner",
  timeline: "Q4",
  budget: "To discuss",
  publication: "private",
  notes: "",
  confirm: "yes",
};

function req(fields, { method = "POST", origin = ORIGIN, type = "application/x-www-form-urlencoded" } = {}) {
  const headers = { "Content-Type": type };
  if (origin) headers.Origin = origin;
  return new Request("https://thor-sec.codethor0.workers.dev/api/request", {
    method,
    headers,
    body: method === "POST" ? new URLSearchParams(fields).toString() : undefined,
  });
}

function env({ limit = true } = {}) {
  return {
    INTAKE_GITHUB_TOKEN: "test-token-not-real",
    INTAKE_LIMITER: { limit: async () => ({ success: limit }) },
    ASSETS: { fetch: async () => new Response("asset") },
  };
}

let calls = [];
test.beforeEach(() => {
  calls = [];
  globalThis.fetch = async (url, init) => {
    calls.push({ url, init });
    return new Response("{}", { status: 201 });
  };
});

test("valid request files one issue and redirects", async () => {
  const res = await handleIntake(req(VALID), env());
  assert.equal(res.status, 303);
  assert.equal(res.headers.get("Location"), SUCCESS_URL);
  assert.equal(calls.length, 1);
  assert.match(calls[0].url, /repos\/codethor0\/thor-sec-intake\/issues$/);
  const issue = JSON.parse(calls[0].init.body);
  assert.ok(issue.title.length <= 120);
  assert.match(issue.body, /Request ID:/);
  assert.doesNotMatch(issue.body, /User-Agent|CF-Connecting-IP|test-token-not-real/i);
});

test("mentions in submitted text are neutralized", async () => {
  await handleIntake(req({ ...VALID, notes: "cc @someone about #12" }), env());
  const issue = JSON.parse(calls[0].init.body);
  assert.doesNotMatch(issue.body, /@someone|#12/);
});

for (const [label, fields] of [
  ["missing name", { ...VALID, name: "" }],
  ["invalid email", { ...VALID, email: "not-an-email" }],
  ["missing question", { ...VALID, question: "" }],
  ["oversized value", { ...VALID, question: "x".repeat(2501) }],
  ["newline in single-line field", { ...VALID, name: "a\nb" }],
  ["invalid authorization", { ...VALID, authorization: "admin" }],
  ["missing confirmation", { ...VALID, confirm: "" }],
]) {
  test(`rejects ${label}`, async () => {
    const res = await handleIntake(req(fields), env());
    assert.equal(res.status, 400);
    assert.equal(calls.length, 0);
    assert.doesNotMatch(await res.text(), /not-an-email|admin/);
  });
}

test("honeypot returns generic success without filing", async () => {
  const res = await handleIntake(req({ ...VALID, website: "spam" }), env());
  assert.equal(res.status, 303);
  assert.equal(calls.length, 0);
});

test("GET is rejected with 405", async () => {
  const res = await handleIntake(req(null, { method: "GET" }), env());
  assert.equal(res.status, 405);
  assert.equal(res.headers.get("Allow"), "POST");
});

test("untrusted and missing Origin are rejected", async () => {
  assert.equal((await handleIntake(req(VALID, { origin: "https://evil.example" }), env())).status, 403);
  assert.equal((await handleIntake(req(VALID, { origin: null }), env())).status, 403);
  assert.equal(calls.length, 0);
});

test("wrong content type is rejected", async () => {
  assert.equal((await handleIntake(req(VALID, { type: "application/json" }), env())).status, 415);
  assert.equal((await handleIntake(req(VALID, { type: "multipart/form-data; boundary=x" }), env())).status, 415);
});

test("oversized body is rejected", async () => {
  const res = await handleIntake(req({ ...VALID, notes: "x".repeat(MAX_BODY_BYTES) }), env());
  assert.equal(res.status, 413);
  assert.equal(calls.length, 0);
});

test("rate limit returns 429", async () => {
  assert.equal((await handleIntake(req(VALID), env({ limit: false }))).status, 429);
  assert.equal(calls.length, 0);
});

test("missing secret fails closed", async () => {
  const e = env();
  delete e.INTAKE_GITHUB_TOKEN;
  assert.equal((await handleIntake(req(VALID), e)).status, 503);
});

test("GitHub failure returns generic 503", async () => {
  globalThis.fetch = async () => new Response("secret internals", { status: 500 });
  const res = await handleIntake(req(VALID), env());
  assert.equal(res.status, 503);
  assert.doesNotMatch(await res.text(), /secret internals/);
});

test("responses carry security headers", async () => {
  const res = await handleIntake(req(null, { method: "GET" }), env());
  for (const h of ["Content-Security-Policy", "X-Content-Type-Options", "X-Frame-Options", "Referrer-Policy", "X-Robots-Tag"]) {
    assert.ok(res.headers.get(h), h);
  }
  assert.equal(res.headers.get("Cache-Control"), "no-store");
});

test("other paths are served from static assets", async () => {
  const res = await worker.fetch(new Request("https://thor-sec.codethor0.workers.dev/work.html"), env());
  assert.equal(await res.text(), "asset");
});

// A request whose body arrives as a stream with no Content-Length header.
function streamReq(chunks, headers = {}) {
  let pulled = 0;
  const body = new ReadableStream({
    pull(controller) {
      if (pulled < chunks.length) controller.enqueue(chunks[pulled++]);
      else controller.close();
    },
  });
  const request = {
    method: "POST",
    headers: new Headers({ Origin: ORIGIN, "Content-Type": "application/x-www-form-urlencoded", ...headers }),
    body,
  };
  return { request, pulled: () => pulled };
}

const enc = new TextEncoder();
const VALID_BYTES = enc.encode(new URLSearchParams(VALID).toString());

test("missing limiter binding fails closed", async () => {
  const e = env();
  delete e.INTAKE_LIMITER;
  const res = await handleIntake(req(VALID), e);
  assert.equal(res.status, 503);
  assert.equal(calls.length, 0);
});

test("limiter error fails closed", async () => {
  const e = env();
  e.INTAKE_LIMITER = { limit: async () => { throw new Error("limiter down"); } };
  const res = await handleIntake(req(VALID), e);
  assert.equal(res.status, 503);
  assert.doesNotMatch(await res.text(), /limiter down/);
  assert.equal(calls.length, 0);
});

test("oversized streamed body without Content-Length is rejected early", async () => {
  const chunk = new Uint8Array(4096).fill(0x61);
  const { request, pulled } = streamReq(Array.from({ length: 64 }, () => chunk));
  const res = await handleIntake(request, env());
  assert.equal(res.status, 413);
  assert.equal(calls.length, 0);
  assert.ok(pulled() < 64, "stream was cancelled before it was fully read");
});

test("misleading Content-Length does not bypass the limit", async () => {
  const chunk = new Uint8Array(8192).fill(0x61);
  const { request } = streamReq([chunk, chunk, chunk, chunk], { "Content-Length": "10" });
  const res = await handleIntake(request, env());
  assert.equal(res.status, 413);
  assert.equal(calls.length, 0);
});

test("valid body streamed in one-byte chunks is accepted", async () => {
  const { request } = streamReq(Array.from(VALID_BYTES, (b) => Uint8Array.of(b)));
  const res = await handleIntake(request, env());
  assert.equal(res.status, 303);
  assert.equal(calls.length, 1);
});

test("multibyte UTF-8 split across chunks is decoded intact", async () => {
  const question = "Pr\u00fcfung \u6e2c\u8a66 \u2603 authorization boundary";
  const bytes = enc.encode(new URLSearchParams({ ...VALID, question }).toString());
  const { request } = streamReq(Array.from(bytes, (b) => Uint8Array.of(b)));
  const res = await handleIntake(request, env());
  assert.equal(res.status, 303);
  assert.match(JSON.parse(calls[0].init.body).body, /Pr\u00fcfung \u6e2c\u8a66 \u2603/);
});

test("body at exactly the limit is read; one byte more is rejected", async () => {
  const exact = new Uint8Array(MAX_BODY_BYTES).fill(0x61);
  assert.equal((await readBody(streamReq([exact]).request)).length, MAX_BODY_BYTES);
  assert.equal(await readBody(streamReq([exact, Uint8Array.of(0x61)]).request), null);
});

test("empty body is treated as empty input", async () => {
  assert.equal(await readBody({ body: null }), "");
});
