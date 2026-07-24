import assert from "node:assert/strict";
import { createHmac } from "node:crypto";

const apiUrl = (process.env.DARKTTK_API_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");
const secret = process.env.WORKSPACE_IDENTITY_SECRET;
assert.ok(secret, "WORKSPACE_IDENTITY_SECRET is required");

const timestamp = Math.floor(Date.now() / 1000).toString();
const identity = {
  email: `rc-e2e-${Date.now()}@example.com`,
  display_name: "RC E2E",
};
const canonical = `${timestamp}\n${identity.email}\n${identity.display_name}`;
const signature = createHmac("sha256", secret).update(canonical).digest("hex");

const exchange = await fetch(`${apiUrl}/v1/auth/workspace-exchange`, {
  method: "POST",
  headers: {
    "content-type": "application/json",
    "x-workspace-timestamp": timestamp,
    "x-workspace-signature": signature,
  },
  body: JSON.stringify(identity),
});
assert.equal(exchange.status, 200, await exchange.text());
const tokens = await exchange.json();
assert.ok(tokens.access_token);
assert.ok(tokens.refresh_token);

const authorization = { authorization: `Bearer ${tokens.access_token}` };
const [dashboardResponse, operationsResponse, costsResponse] = await Promise.all([
  fetch(`${apiUrl}/v1/dashboard`, { headers: authorization }),
  fetch(`${apiUrl}/v1/operations/status`, { headers: authorization }),
  fetch(`${apiUrl}/v1/operations/costs/summary`, { headers: authorization }),
]);
assert.equal(dashboardResponse.status, 200, await dashboardResponse.text());
assert.equal(operationsResponse.status, 200, await operationsResponse.text());
assert.equal(costsResponse.status, 200, await costsResponse.text());

const dashboard = await dashboardResponse.json();
const operations = await operationsResponse.json();
const costs = await costsResponse.json();
assert.equal(dashboard.daily_limit, 5);
assert.equal(operations.is_mock, false);
assert.equal(costs.currency, "BRL");

const mfaSetup = await fetch(`${apiUrl}/v1/auth/mfa/setup`, {
  method: "POST",
  headers: authorization,
});
assert.equal(mfaSetup.status, 200, await mfaSetup.text());
const mfa = await mfaSetup.json();

function decodeBase32(value) {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  let bits = "";
  for (const character of value.replace(/=+$/, "").toUpperCase()) {
    bits += alphabet.indexOf(character).toString(2).padStart(5, "0");
  }
  return Buffer.from(
    bits.match(/.{8}/g)?.map((byte) => Number.parseInt(byte, 2)) || [],
  );
}

function currentTotp(secretValue) {
  const step = Math.floor(Date.now() / 30_000);
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(step));
  const digest = createHmac("sha1", decodeBase32(secretValue)).update(counter).digest();
  const offset = digest[digest.length - 1] & 0x0f;
  const number = (digest.readUInt32BE(offset) & 0x7fffffff) % 1_000_000;
  return number.toString().padStart(6, "0");
}

const mfaConfirm = await fetch(`${apiUrl}/v1/auth/mfa/confirm`, {
  method: "POST",
  headers: { ...authorization, "content-type": "application/json" },
  body: JSON.stringify({ code: currentTotp(mfa.secret) }),
});
assert.equal(mfaConfirm.status, 200, await mfaConfirm.text());
const recoveryCodes = (await mfaConfirm.json()).recovery_codes;
assert.equal(recoveryCodes.length, 8);
const recoveryRotation = await fetch(`${apiUrl}/v1/auth/mfa/recovery-codes`, {
  method: "POST",
  headers: { ...authorization, "content-type": "application/json" },
  body: JSON.stringify({ code: recoveryCodes[0] }),
});
assert.equal(recoveryRotation.status, 200, await recoveryRotation.text());
assert.equal((await recoveryRotation.json()).recovery_codes.length, 8);

const sourceResponse = await fetch(`${apiUrl}/v1/intelligence/trend-sources`, {
  method: "POST",
  headers: { ...authorization, "content-type": "application/json" },
  body: JSON.stringify({
    name: `RC authorized source ${Date.now()}`,
    connector_type: "api",
    endpoint_url: "https://example.com/authorized-api",
    terms_url: "https://example.com/terms",
    authorization_confirmed: true,
  }),
});
assert.equal(sourceResponse.status, 201, await sourceResponse.text());
const source = await sourceResponse.json();
const trendResponse = await fetch(`${apiUrl}/v1/intelligence/trends`, {
  method: "POST",
  headers: { ...authorization, "content-type": "application/json" },
  body: JSON.stringify({
    source_id: source.id,
    topic: "Materiais que se autorreparam",
    category: "Engenharia",
    relevance_reason: "Sinal autorizado usado para o gate da release.",
    growth_percent: 84.5,
    interest_volume: 12000,
    competition: "low",
    retention_score: 91,
    share_score: 87,
    sensitivity_risk: "low",
    saturation_risk: "low",
    suggested_approach: "Explicação original baseada em fontes.",
    likely_audience: "Curiosos por ciência",
    valid_until: new Date(Date.now() + 4 * 86_400_000).toISOString(),
  }),
});
assert.equal(trendResponse.status, 201, await trendResponse.text());
const seriesResponse = await fetch(`${apiUrl}/v1/intelligence/series`, {
  method: "POST",
  headers: { ...authorization, "content-type": "application/json" },
  body: JSON.stringify({
    name: `RC Engineering ${Date.now()}`,
    description: "Série persistente validada pela jornada de release.",
    cadence: "weekly",
    target_episode_count: 12,
  }),
});
assert.equal(seriesResponse.status, 201, await seriesResponse.text());
assert.equal((await seriesResponse.json()).status, "active");

const refresh = await fetch(`${apiUrl}/v1/auth/refresh`, {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({ refresh_token: tokens.refresh_token }),
});
assert.equal(refresh.status, 200, await refresh.text());
const rotated = await refresh.json();
assert.notEqual(rotated.refresh_token, tokens.refresh_token);

console.log("RC E2E passed: migrations, identity, 2FA, intelligence, operations, costs and token rotation.");
