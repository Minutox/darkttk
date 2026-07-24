import assert from "node:assert/strict";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(
    new Request("http://localhost/", { headers: { accept: "text/html" } }),
    { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } },
    { waitUntil() {}, passThroughOnException() {} },
  );
}

test("server-renders the DarkTTK operational dashboard", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);
  const html = await response.text();
  assert.match(html, /<title>DarkTTK — Content Intelligence<\/title>/i);
  assert.match(html, /DarkTTK/);
  assert.match(html, /Boa tarde/);
  assert.match(html, /Aguardando aprovação/i);
  assert.match(html, /Oportunidade do dia/i);
  assert.match(html, /Publicações/i);
  assert.match(html, /Métricas/i);
  assert.match(html, /Experimentos/i);
  assert.match(html, /Opera\u00e7\u00f5es/i);
  assert.match(html, /Pr\u00e9via operacional/i);
  assert.match(html, /\/og\.png/i);
  assert.doesNotMatch(html, /codex-preview|react-loading-skeleton/i);
});
