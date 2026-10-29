// The "connect a cloud" form, driven by what the server says each provider needs (/api/v1/cloud/providers):
// fields to render, which of them are the credential, and the request body. No Vue here, so it is unit-tested.

const LABEL = {
  url: "API address", auth_url: "Identity (Keystone) URL", org: "Organization", region: "Region", interface: "Endpoint interface",
  pool: "Resource pool", verify_tls: "Check the TLS certificate", tenant_id: "Tenant ID", subscription_id: "Subscription ID",
  project: "Project ID", token_id: "API token ID", token_secret: "API token secret", api_token: "API token",
  application_credential_id: "Application credential ID", application_credential_secret: "Application credential secret",
  api_key: "API key", secret_key: "Secret key", access_key_id: "Access key ID", secret_access_key: "Secret access key",
  client_id: "Client ID", client_secret: "Client secret", service_account_json: "Service account key (JSON)",
};
const PLACEHOLDER = {
  url: "https://", auth_url: "https://identity.example.com/v3", region: "e.g. ap-southeast-7", pool: "only this pool's VMs (optional)",
  token_id: "user@realm!tokenname", org: "your organization name", project: "my-project-id", interface: "public",
};
const SECRET_TEXTAREA = new Set(["service_account_json"]);

export function fieldsFor(spec) {
  const out = [];
  for (const [keys, required, secret] of [[spec.config, true, false], [spec.optional || [], false, false], [spec.secret, true, true]]) {
    for (const key of keys) {
      const type = key === "verify_tls" ? "switch" : secret ? (SECRET_TEXTAREA.has(key) ? "textarea" : "password") : "text";
      out.push({ key, label: LABEL[key] || key, type, required, secret, placeholder: PLACEHOLDER[key] || "" });
    }
  }
  return out;
}

const blank = (v) => v === undefined || v === null || (typeof v === "string" && !v.trim());

export function bodyFor(spec, name, values) {
  const config = {}, secret = {};
  for (const f of fieldsFor(spec)) {
    const v = values[f.key];
    if (blank(v)) continue;
    (f.secret ? secret : config)[f.key] = typeof v === "string" ? v.trim() : v;
  }
  return { provider: spec.id, name: (name || "").trim(), config, secret };
}

export function missing(spec, name, values) {
  return [...(blank(name) ? ["name"] : []), ...fieldsFor(spec).filter((f) => f.required && blank(values[f.key])).map((f) => f.key)];
}

const TONE = { ok: "ok", agent_silent: "bad", error: "bad", stopped_in_cloud: "warn", transition: "info", gone: "neutral", not_monitored: "neutral" };
export const verdictTone = (code) => TONE[code] || "neutral";
