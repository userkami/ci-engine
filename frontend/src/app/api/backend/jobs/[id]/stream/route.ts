import { NextRequest, NextResponse } from "next/server";
import { BackendRequestError, provisionBackendIdentity } from "@/lib/backend";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await params;
    const { access_token } = await provisionBackendIdentity();
    const backend = process.env.BACKEND_PROXY_URL ?? "http://localhost:8000";
    const response = await fetch(`${backend}/api/jobs/${encodeURIComponent(id)}/stream`, {
      headers: { Authorization: `Bearer ${access_token}` },
      cache: "no-store",
      signal: request.signal,
    });
    if (!response.ok || !response.body) {
      return NextResponse.json({ error: "Unable to stream this job" }, { status: response.ok ? 502 : response.status });
    }
    return new Response(response.body, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",
      },
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof BackendRequestError ? error.message : "Stream unavailable" },
      { status: error instanceof BackendRequestError ? error.status : 502 },
    );
  }
}
