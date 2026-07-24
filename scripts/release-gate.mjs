import assert from "node:assert/strict";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const requiredFiles = [
  ".openai/hosting.json",
  "release-manifest.json",
  "docs/RC1-PROMOTION-ROLLBACK.md",
  "docs/RC1-FINAL-EVIDENCE.md",
  ".github/workflows/ci.yml",
  ".github/workflows/rc-e2e.yml",
  "services/api/migrations/0009_intelligence_series.sql",
  "drizzle/0009_intelligence_series.sql",
  "public/og.png",
];
for (const file of requiredFiles) {
  assert.ok(existsSync(resolve(root, file)), `Required release file missing: ${file}`);
}

const manifest = JSON.parse(readFileSync(resolve(root, "release-manifest.json"), "utf8"));
const packageJson = JSON.parse(readFileSync(resolve(root, "package.json"), "utf8"));
assert.equal(packageJson.version, manifest.version, "Package and release versions differ");
assert.equal(manifest.checkpoint, 4);

const migrationIds = (directory) =>
  readdirSync(resolve(root, directory))
    .filter((name) => /^\d{4}_.+\.sql$/.test(name))
    .map((name) => name.slice(0, 4))
    .sort();
const apiMigrations = migrationIds("services/api/migrations");
const siteMigrations = migrationIds("drizzle");
assert.equal(apiMigrations[0], manifest.migration_range[0]);
assert.equal(siteMigrations[0], "0000");
assert.equal(apiMigrations.at(-1), siteMigrations.at(-1), "Latest schema migrations differ");
assert.equal(Number(apiMigrations.at(-1)), manifest.schema_version);

const journal = JSON.parse(
  readFileSync(resolve(root, "drizzle/meta/_journal.json"), "utf8"),
);
assert.equal(journal.entries.at(-1).idx, manifest.schema_version);
assert.equal(journal.entries.length, manifest.schema_version + 1);

const envExample = readFileSync(resolve(root, ".env.example"), "utf8");
for (const key of [
  "WORKSPACE_IDENTITY_SECRET",
  "ACCOUNT_DELIVERY_MODE",
  "RESEND_API_KEY",
  "ACCOUNT_EMAIL_FROM",
  "PASSWORD_RECOVERY_URL",
]) {
  assert.match(envExample, new RegExp(`^${key}=`, "m"), `Missing ${key} in .env.example`);
}

const hosting = JSON.parse(readFileSync(resolve(root, ".openai/hosting.json"), "utf8"));
assert.equal(hosting.d1, "DB");
assert.equal(hosting.r2, "MEDIA");

const productionCompose = readFileSync(resolve(root, "docker-compose.prod.yml"), "utf8");
assert.match(productionCompose, /AUTO_CREATE_SCHEMA:\s*"false"/);
assert.doesNotMatch(productionCompose, /ACCOUNT_DELIVERY_MODE:\s*mock/);

console.log(
  `Release gate passed: ${manifest.version}, schema ${manifest.schema_version}, ${manifest.required_gates.length} required gates.`,
);
