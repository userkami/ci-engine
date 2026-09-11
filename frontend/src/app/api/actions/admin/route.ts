import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_PROXY_URL ?? "http://localhost:8000";

function unauthorized() {
  return NextResponse.json({ error: "Missing or invalid admin token" }, { status: 401 });
}

function extractAdminToken(req: NextRequest): string | null {
  const header = req.headers.get("x-admin-token");
  if (header && header.trim()) return header.trim();
  // Also check body for token (in case header is stripped by some proxies)
  return null;
}

/** GET /api/actions/admin/config — fetch all config entries. */
export async function GET(req: NextRequest) {
  const token = extractAdminToken(req);
  if (!token) return unauthorized();

  try {
    const res = await fetch(`${BACKEND_URL}/api/admin/config`, {
      method: "GET",
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        "X-Admin-Token": token,
      },
    });
    const body = await res.json();
    return NextResponse.json(body, { status: res.status });
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Backend unavailable" },
      { status: 502 },
    );
  }
}

/** PUT /api/actions/admin/config — update config entries. */
export async function PUT(req: NextRequest) {
  const token = extractAdminToken(req);
  if (!token) return unauthorized();

  try {
    const body = (await req.json()) as { updates?: Record<string, string> };
    if (!body || typeof body.updates !== "object" || body.updates === null) {
      return NextResponse.json(
        { error: "Request body must include an 'updates' object" },
        { status: 422 },
      );
    }
    const res = await fetch(`${BACKEND_URL}/api/admin/config`, {
      method: "PUT",
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        "X-Admin-Token": token,
      },
      body: JSON.stringify({ updates: body.updates }),
    });
    const responseBody = await res.json();
    return NextResponse.json(responseBody, { status: res.status });
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Backend unavailable" },
      { status: 502 },
    );
  }
}

/** POST /api/actions/admin/config/test — test a model spec without saving. */
export async function POST(req: NextRequest) {
  const token = extractAdminToken(req);
  if (!token) return unauthorized();

  try {
    const body = (await req.json()) as {
      role?: string;
      model_spec?: string;
    };
    if (!body || typeof body.model_spec !== "string" || !body.model_spec.trim()) {
      return NextResponse.json(
        { error: "Request body must include a 'model_spec' string" },
        { status: 422 },
      );
    }
    const res = await fetch(`${BACKEND_URL}/api/admin/config/test`, {
      method: "POST",
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        "X-Admin-Token": token,
      },
      body: JSON.stringify({
        role: body.role ?? "fast",
        model_spec: body.model_spec,
      }),
    });
    const responseBody = await res.json();
    return NextResponse.json(responseBody, { status: res.status });
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Backend unavailable" },
      { status: 502 },
    );
  }
}
