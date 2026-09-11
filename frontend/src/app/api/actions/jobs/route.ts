import { NextRequest, NextResponse } from "next/server";

import { createResearchJob } from "@/lib/backend";

export const runtime = "nodejs";

/** POST /api/actions/jobs — start a research job (server-side auth). */
export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as {
      target_company?: unknown;
      competitor?: unknown;
    };
    const target = typeof body.target_company === "string" ? body.target_company.trim() : "";
    const competitor = typeof body.competitor === "string" ? body.competitor.trim() : "";
    if (!target || !competitor) {
      return NextResponse.json(
        { error: "target_company and competitor are required" },
        { status: 422 },
      );
    }
    const job = await createResearchJob(target, competitor);
    return NextResponse.json(job, { status: 201 });
  } catch (err) {
    return NextResponse.json(
      { error: errorMessage(err) },
      { status: errorStatus(err) },
    );
  }
}

function errorMessage(err: unknown): string {
  if (err instanceof Error && err.message) return err.message;
  return "Something went wrong";
}

function errorStatus(err: unknown): number {
  if (
    err instanceof Error &&
    typeof (err as unknown as { status?: unknown }).status === "number"
  ) {
    return (err as unknown as { status: number }).status;
  }
  return 500;
}