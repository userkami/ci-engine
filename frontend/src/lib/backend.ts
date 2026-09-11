/**
 * Server-only bridge to the FastAPI backend.
 *
 * `provisionBackendIdentity()` exchanges a verified NextAuth session for a
 * backend-signed access token (upserting the user + default credit
 * profile). Every protected backend call mints one, so tokens stay
 * short-lived and the user row always exists.
 *
 * IMPORTANT: this module must only ever be imported from server-side code
 * (route handlers / server components) — it reads the session cookie.
 */
import { getServerSession } from "next-auth";

import type { BattlecardRecord } from "@/types";
import { authOptions } from "./auth";

const BACKEND_URL = process.env.BACKEND_PROXY_URL ?? "http://localhost:8000";

export class BackendRequestError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
  }
}

interface ProvisionResult {
  access_token: string;
  user_id: string;
  email: string;
  balance: number;
}

interface JobCreateResult {
  job_id: string;
  status: string;
}

export async function provisionBackendIdentity(): Promise<ProvisionResult> {
  const session = await getServerSession(authOptions);
  if (!session?.user?.email) {
    throw new BackendRequestError("You must be signed in", 401);
  }
  const res = await fetch(`${BACKEND_URL}/api/auth/provision`, {
    method: "POST",
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: session.user.email,
      name: session.user.name,
      image_url: session.user.image,
    }),
  });
  return readJson<ProvisionResult>(res);
}

export async function createResearchJob(
  targetCompany: string,
  competitor: string,
): Promise<JobCreateResult> {
  const { access_token } = await provisionBackendIdentity();
  const res = await fetch(`${BACKEND_URL}/api/jobs/create`, {
    method: "POST",
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${access_token}`,
    },
    body: JSON.stringify({
      target_company: targetCompany,
      competitor,
    }),
  });
  return readJson<JobCreateResult>(res);
}

export async function getBattlecard(
  id: string,
): Promise<BattlecardRecord> {
  const { access_token } = await provisionBackendIdentity();
  const res = await fetch(
    `${BACKEND_URL}/api/battlecards/${encodeURIComponent(id)}`,
    {
      cache: "no-store",
      headers: { Authorization: `Bearer ${access_token}` },
    },
  );
  return readJson<BattlecardRecord>(res);
}

async function readJson<T>(res: Response): Promise<T> {
  let payload: unknown = null;
  try {
    payload = await res.json();
  } catch {
    payload = null;
  }
  if (!res.ok) {
    let detail = `Backend error (${res.status})`;
    if (
      payload &&
      typeof payload === "object" &&
      typeof (payload as { detail?: unknown }).detail === "string"
    ) {
      detail = (payload as { detail: string }).detail;
    }
    throw new BackendRequestError(detail, res.status);
  }
  return payload as T;
}