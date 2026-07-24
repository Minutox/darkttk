import { getChatGPTUser } from "../../../chatgpt-auth";
import { getServerApiAccessToken } from "../../../api-client";

async function proxy(
  method: "GET" | "POST" | "DELETE",
  path: string,
  payload?: Record<string, unknown>,
): Promise<Response> {
  const user = await getChatGPTUser();
  if (!user) return Response.json({ code: "authentication_required" }, { status: 401 });
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5_000);
  try {
    const session = await getServerApiAccessToken(user, controller.signal);
    const upstream = await fetch(`${session.apiUrl}${path}`, {
      method,
      headers: {
        Authorization: `Bearer ${session.accessToken}`,
        ...(payload ? { "Content-Type": "application/json" } : {}),
      },
      body: payload ? JSON.stringify(payload) : undefined,
      cache: "no-store",
      signal: controller.signal,
    });
    const body = await upstream.text();
    return new Response(body || null, {
      status: upstream.status,
      headers: { "Content-Type": upstream.headers.get("content-type") || "application/json" },
    });
  } catch {
    return Response.json({ code: "api_unavailable" }, { status: 503 });
  } finally {
    clearTimeout(timeout);
  }
}

export async function GET(): Promise<Response> {
  return proxy("GET", "/v1/auth/mfa");
}

export async function POST(request: Request): Promise<Response> {
  const body = await request.json().catch(() => null) as { kind?: string; code?: string } | null;
  if (body?.kind === "setup") return proxy("POST", "/v1/auth/mfa/setup");
  if (body?.kind === "confirm" && body.code) {
    return proxy("POST", "/v1/auth/mfa/confirm", { code: body.code });
  }
  if (body?.kind === "regenerate" && body.code) {
    return proxy("POST", "/v1/auth/mfa/recovery-codes", { code: body.code });
  }
  return Response.json({ code: "invalid_security_action" }, { status: 422 });
}

export async function DELETE(request: Request): Promise<Response> {
  const body = await request.json().catch(() => null) as { code?: string } | null;
  if (!body?.code) return Response.json({ code: "mfa_code_required" }, { status: 422 });
  return proxy("DELETE", "/v1/auth/mfa", { code: body.code });
}
