// THOR-SEC research-request intake.
// The only server-side route on the Cloudflare mirror: POST /api/request.
// Accepts a plain HTML form, validates it, and files a private issue in the
// intake repository. Stores no visitor telemetry (no IP, User-Agent, location,
// cookies, or raw headers). Every other path is served from static assets.

export const INTAKE_PATH = "/api/request";
export const INTAKE_REPO = "codethor0/thor-sec-intake";
export const SUCCESS_URL = "https://codethor0.github.io/thor-sec/request-received.html";
export const ALLOWED_ORIGINS = new Set([
  "https://codethor0.github.io",
  "https://thor-sec.codethor0.workers.dev",
]);
export const MAX_BODY_BYTES = 24 * 1024;
export const HONEYPOT = "website";

export const AUTHORIZATION = {
  owner: "Owner or authorized representative of the systems",
  written: "Written authorization exists",
  planning: "Planning or scoping only",
  other: "Other / needs discussion",
};
export const PUBLICATION = {
  public: "Public",
  delayed: "Delayed publication",
  private: "Private",
  unsure: "Not sure",
};

// name: [maxLength, required, singleLine]
export const FIELDS = {
  name: [120, true, true],
  email: [254, true, true],
  organization: [200, false, true],
  question: [2500, true, false],
  objective: [1500, false, false],
  scope: [2000, false, false],
  timeline: [200, false, true],
  budget: [200, false, true],
  notes: [2500, false, false],
};

const LABELS = {
  name: "Name",
  email: "Email",
  organization: "Organization",
  question: "Research question",
  objective: "Objective / intended use",
  scope: "Scope / systems involved",
  authorization: "Authorization status",
  timeline: "Timeline",
  budget: "Budget range",
  publication: "Publication preference",
  notes: "Notes",
};

const SECURITY_HEADERS = {
  "Cache-Control": "no-store",
  "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
  "Referrer-Policy": "no-referrer",
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "DENY",
  "Permissions-Policy": "accelerometer=(), camera=(), geolocation=(), microphone=(), payment=(), usb=()",
  "X-Robots-Tag": "noindex",
};

const CONTROL = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/;
const EMAIL = /^[^\s@<>()[\]\\,;:"]+@[^\s@<>()[\]\\,;:"]+\.[^\s@<>()[\]\\,;:"]{2,}$/;

function reply(status, message, extra = {}) {
  const body = `${message}\n\nIf this keeps happening, email codethor@gmail.com instead.\n`;
  return new Response(status === 303 ? null : body, {
    status,
    headers: { ...SECURITY_HEADERS, "Content-Type": "text/plain; charset=utf-8", ...extra },
  });
}

const accepted = () => reply(303, "", { Location: SUCCESS_URL });

export function validate(params) {
  const out = {};
  for (const [field, [max, required, singleLine]] of Object.entries(FIELDS)) {
    let value = (params.get(field) || "").replace(/\r\n?/g, "\n").trim();
    if (CONTROL.test(value)) return null;
    if (singleLine && value.includes("\n")) return null;
    if (value.length > max) return null;
    if (required && !value) return null;
    out[field] = value;
  }
  if (!EMAIL.test(out.email)) return null;
  const authorization = params.get("authorization") || "";
  if (!Object.hasOwn(AUTHORIZATION, authorization)) return null;
  out.authorization = AUTHORIZATION[authorization];
  const publication = params.get("publication") || "unsure";
  if (!Object.hasOwn(PUBLICATION, publication)) return null;
  out.publication = PUBLICATION[publication];
  if (params.get("confirm") !== "yes") return null;
  return out;
}

// Stops @mentions and #references in submitted text from notifying anyone.
const quiet = (s) => s.replace(/@/g, "@​").replace(/#(\d)/g, "#​$1");

function fence(value) {
  const longest = Math.max(2, ...(value.match(/`+/g) || []).map((r) => r.length));
  const f = "`".repeat(longest + 1);
  return `${f}text\n${quiet(value) || "(not provided)"}\n${f}`;
}

export function buildIssue(data, requestId, submittedAt) {
  const who = data.organization || data.name;
  const title = quiet(`Research request: ${who} - ${data.question}`.replace(/\s+/g, " ")).slice(0, 120);
  const sections = Object.keys(LABELS).map((k) => `### ${LABELS[k]}\n\n${fence(data[k])}`);
  const body = [
    `Request ID: \`${requestId}\``,
    `Submitted (UTC): ${submittedAt}`,
    "",
    ...sections,
    "",
    "Submission is for scoping only and does not create an engagement.",
  ].join("\n");
  return { title, body };
}

export async function handleIntake(request, env) {
  if (request.method !== "POST") return reply(405, "Method not allowed.", { Allow: "POST" });
  if (!ALLOWED_ORIGINS.has(request.headers.get("Origin") || "")) return reply(403, "Request origin not allowed.");
  const type = (request.headers.get("Content-Type") || "").split(";")[0].trim().toLowerCase();
  if (type !== "application/x-www-form-urlencoded") return reply(415, "Unsupported content type.");
  if (Number(request.headers.get("Content-Length") || 0) > MAX_BODY_BYTES) return reply(413, "Request too large.");

  if (env.INTAKE_LIMITER) {
    const { success } = await env.INTAKE_LIMITER.limit({ key: INTAKE_PATH });
    if (!success) return reply(429, "Too many requests. Please try again in a minute.");
  }

  const raw = await request.text();
  if (new TextEncoder().encode(raw).length > MAX_BODY_BYTES) return reply(413, "Request too large.");
  const params = new URLSearchParams(raw);

  if (params.get(HONEYPOT)) return accepted();

  const data = validate(params);
  if (!data) return reply(400, "The request is missing required fields or contains invalid values. Please go back and check the form.");

  if (!env.INTAKE_GITHUB_TOKEN) return reply(503, "The request form is temporarily unavailable.");
  const { title, body } = buildIssue(data, crypto.randomUUID(), new Date().toISOString());
  let ok = false;
  try {
    const res = await fetch(`https://api.github.com/repos/${INTAKE_REPO}/issues`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.INTAKE_GITHUB_TOKEN}`,
        Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "thor-sec-intake",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ title, body }),
    });
    ok = res.status === 201;
  } catch {
    ok = false;
  }
  if (!ok) return reply(503, "The request could not be recorded right now.");
  return accepted();
}

export default {
  async fetch(request, env) {
    if (new URL(request.url).pathname === INTAKE_PATH) return handleIntake(request, env);
    return env.ASSETS.fetch(request);
  },
};
