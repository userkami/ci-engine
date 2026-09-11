import { NextRequest, NextResponse } from "next/server";

import { getBattlecard } from "@/lib/backend";

export const runtime = "nodejs";

/** GET /api/actions/battlecards/{id} — fetch a saved battlecard. */
export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  try {
    const card = await getBattlecard(id);
    return NextResponse.json(card);
  } catch (err) {
    const status =
      err instanceof Error &&
      typeof (err as unknown as { status?: unknown }).status === "number"
        ? (err as unknown as { status: number }).status
        : 500;
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Something went wrong" },
      { status },
    );
  }
}