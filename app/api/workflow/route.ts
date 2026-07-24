import { getChatGPTUser } from "../../chatgpt-auth";
import { getServerApiAccessToken } from "../../api-client";

type WorkflowAction =
  | { kind: "approval_decision"; approval_id: string; decision: "approved" | "rejected" | "changes_requested"; note?: string }
  | { kind: "schedule"; project_id: string; scheduled_for: string; timezone: string; note?: string };

function validId(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value);
}

export async function POST(request: Request): Promise<Response> {
  const user = await getChatGPTUser();
  if (!user) return Response.json({ code: "authentication_required" }, { status: 401 });

  let action: WorkflowAction;
  try {
    action = await request.json() as WorkflowAction;
  } catch {
    return Response.json({ code: "invalid_json" }, { status: 400 });
  }

  let path: string;
  let payload: Record<string, unknown>;
  if (
    action.kind === "approval_decision"
    && validId(action.approval_id)
    && ["approved", "rejected", "changes_requested"].includes(action.decision)
  ) {
    if (action.decision !== "approved" && !(action.note || "").trim()) {
      return Response.json({ code: "decision_note_required" }, { status: 422 });
    }
    path = `/v1/workflow/approvals/${action.approval_id}/decision`;
    payload = { decision: action.decision, note: action.note };
  } else if (
    action.kind === "schedule"
    && validId(action.project_id)
    && !Number.isNaN(Date.parse(action.scheduled_for))
    && action.timezone.length >= 3
  ) {
    path = `/v1/workflow/projects/${action.project_id}/schedule`;
    payload = {
      scheduled_for: action.scheduled_for,
      timezone: action.timezone,
      note: action.note,
    };
  } else {
    return Response.json({ code: "invalid_workflow_action" }, { status: 422 });
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5_000);
  try {
    const session = await getServerApiAccessToken(user, controller.signal);
    const upstream = await fetch(`${session.apiUrl}${path}`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${session.accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
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
