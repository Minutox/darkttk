import { getChatGPTUser } from "../../chatgpt-auth";
import { getServerApiAccessToken } from "../../api-client";

export async function PATCH(request: Request): Promise<Response> {
  const user = await getChatGPTUser();
  if (!user) return Response.json({ code: "authentication_required" }, { status: 401 });
  const body = await request.json().catch(() => null) as {
    project_id?: string;
    scene_id?: string;
    start_ms?: number;
    end_ms?: number;
    trim_start_ms?: number;
    transition?: string;
    motion?: string;
    text_overlay?: Record<string, unknown>;
  } | null;
  if (
    !body?.project_id?.match(/^[0-9a-f-]{36}$/i) ||
    !body.scene_id?.match(/^[0-9a-f-]{36}$/i)
  ) {
    return Response.json({ code: "invalid_scene_reference" }, { status: 422 });
  }
  const { project_id, scene_id, ...changes } = body;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5_000);
  try {
    const session = await getServerApiAccessToken(user, controller.signal);
    const upstream = await fetch(
      `${session.apiUrl}/v1/video/projects/${project_id}/scenes/${scene_id}`,
      {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${session.accessToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(changes),
        cache: "no-store",
        signal: controller.signal,
      },
    );
    return new Response(await upstream.text(), {
      status: upstream.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch {
    return Response.json({ code: "api_unavailable" }, { status: 503 });
  } finally {
    clearTimeout(timeout);
  }
}
