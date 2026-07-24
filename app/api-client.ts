import type { ChatGPTUser } from "./chatgpt-auth";

export type RuntimeSnapshot = {
  mode: "live" | "demo" | "unavailable";
  capturedAt: string;
  message: string;
  dashboard?: {
    published_today: number;
    daily_limit: number;
    awaiting_approval: number;
    in_production: number;
    scheduled: number;
    health: string;
  };
  operations?: {
    status: "ready" | "attention";
    environment: string;
    version: string;
    checks: Record<string, boolean>;
    open_errors: number;
    failed_publications: number;
    last_backup_at: string | null;
    is_mock: boolean;
  };
  costs?: {
    spent_cents: number;
    monthly_limit_cents: number;
    usage_percent: number;
    warning_percent: number;
    hard_stop_enabled: boolean;
    currency: string;
    state: "ok" | "warning" | "blocked";
  };
  approvals?: Array<{
    id: string;
    video_project_id: string;
    project_title: string;
    preview_is_mock: boolean;
    status: string;
    request_note: string | null;
    decision_note: string | null;
    created_at: string;
  }>;
  calendar?: Array<{
    id: string;
    video_project_id: string;
    project_title: string;
    scheduled_for: string;
    status: string;
  }>;
  notifications?: {
    unread_count: number;
    items: Array<{
      id: string;
      title: string;
      message: string;
      kind: string;
      read_at: string | null;
    }>;
  };
  trends?: Array<{
    id: string;
    topic: string;
    category: string;
    relevance_reason: string;
    growth_percent: number;
    interest_volume: number;
    competition: string;
    retention_score: number;
    share_score: number;
    sensitivity_risk: string;
    saturation_risk: string;
    suggested_approach: string;
    likely_audience: string;
    valid_until: string;
  }>;
  series?: Array<{
    id: string;
    name: string;
    description: string;
    cadence: string;
    target_episode_count: number;
    status: string;
    created_at: string;
  }>;
};

function demoSnapshot(message: string): RuntimeSnapshot {
  return {
    mode: "demo",
    capturedAt: new Date().toISOString(),
    message,
  };
}

async function signature(secret: string, canonical: string): Promise<string> {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const value = await crypto.subtle.sign("HMAC", key, encoder.encode(canonical));
  return Array.from(new Uint8Array(value), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function apiFetch<T>(
  url: string,
  path: string,
  accessToken: string,
  signal: AbortSignal,
): Promise<T> {
  const response = await fetch(`${url}${path}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: "no-store",
    signal,
  });
  if (!response.ok) throw new Error(`API ${path} returned ${response.status}`);
  return response.json() as Promise<T>;
}

export async function getServerApiAccessToken(
  user: ChatGPTUser,
  signal: AbortSignal,
): Promise<{ apiUrl: string; accessToken: string }> {
  const apiUrl = process.env.DARKTTK_API_URL?.replace(/\/+$/, "");
  const secret = process.env.WORKSPACE_IDENTITY_SECRET;
  if (!apiUrl || !secret) throw new Error("API integration is not configured.");
  const timestamp = Math.floor(Date.now() / 1000).toString();
  const email = user.email.trim().toLowerCase();
  const displayName = user.displayName.trim();
  const signed = await signature(secret, `${timestamp}\n${email}\n${displayName}`);
  const exchange = await fetch(`${apiUrl}/v1/auth/workspace-exchange`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Workspace-Timestamp": timestamp,
      "X-Workspace-Signature": signed,
    },
    body: JSON.stringify({ email, display_name: displayName }),
    cache: "no-store",
    signal,
  });
  if (!exchange.ok) throw new Error(`Identity exchange returned ${exchange.status}`);
  const tokens = await exchange.json() as { access_token: string };
  return { apiUrl, accessToken: tokens.access_token };
}

export async function getRuntimeSnapshot(user: ChatGPTUser | null): Promise<RuntimeSnapshot> {
  const apiUrl = process.env.DARKTTK_API_URL?.replace(/\/+$/, "");
  const secret = process.env.WORKSPACE_IDENTITY_SECRET;
  if (!apiUrl || !secret || !user) {
    return demoSnapshot("API real não configurada para este ambiente.");
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 4_000);
  try {
    const session = await getServerApiAccessToken(user, controller.signal);
    const [dashboard, operations, costs, approvals, calendar, notifications, trends, series] = await Promise.all([
      apiFetch<NonNullable<RuntimeSnapshot["dashboard"]>>(apiUrl, "/v1/dashboard", session.accessToken, controller.signal),
      apiFetch<NonNullable<RuntimeSnapshot["operations"]>>(apiUrl, "/v1/operations/status", session.accessToken, controller.signal),
      apiFetch<NonNullable<RuntimeSnapshot["costs"]>>(apiUrl, "/v1/operations/costs/summary", session.accessToken, controller.signal),
      apiFetch<NonNullable<RuntimeSnapshot["approvals"]>>(apiUrl, "/v1/workflow/approvals?limit=50", session.accessToken, controller.signal),
      apiFetch<NonNullable<RuntimeSnapshot["calendar"]>>(apiUrl, "/v1/workflow/calendar", session.accessToken, controller.signal),
      apiFetch<NonNullable<RuntimeSnapshot["notifications"]>>(apiUrl, "/v1/workflow/notifications?limit=50", session.accessToken, controller.signal),
      apiFetch<NonNullable<RuntimeSnapshot["trends"]>>(apiUrl, "/v1/intelligence/trends?limit=50", session.accessToken, controller.signal),
      apiFetch<NonNullable<RuntimeSnapshot["series"]>>(apiUrl, "/v1/intelligence/series", session.accessToken, controller.signal),
    ]);
    return {
      mode: "live",
      capturedAt: new Date().toISOString(),
      message: "Dados autenticados carregados da API DarkTTK.",
      dashboard,
      operations,
      costs,
      approvals,
      calendar,
      notifications,
      trends,
      series,
    };
  } catch {
    return {
      mode: "unavailable",
      capturedAt: new Date().toISOString(),
      message: "A API configurada não respondeu com uma sessão válida.",
    };
  } finally {
    clearTimeout(timeout);
  }
}
