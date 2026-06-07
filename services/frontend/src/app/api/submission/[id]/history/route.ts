import { NextResponse } from "next/server";
import { fetchLatencyHistory } from "@/lib/redis";

export const dynamic = "force-dynamic";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const points = await fetchLatencyHistory(id);
  return NextResponse.json({ points });
}
