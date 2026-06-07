import { NextResponse } from "next/server";
import { fetchLeaderboard } from "@/lib/redis";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const entries = await fetchLeaderboard();
    return NextResponse.json({ entries });
  } catch (e) {
    return NextResponse.json(
      { error: String(e), entries: [] },
      { status: 503 },
    );
  }
}
