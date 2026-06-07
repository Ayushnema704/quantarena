import { NextResponse } from "next/server";
import { fetchSubmissionSnapshot } from "@/lib/redis";

const SUBMISSION_API_URL = process.env.SUBMISSION_API_URL ?? "http://localhost:8000";

export const dynamic = "force-dynamic";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const snap = await fetchSubmissionSnapshot(id);
  if (!snap) return NextResponse.json({ error: "not found" }, { status: 404 });
  return NextResponse.json(snap);
}

export async function POST(
  req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  try {
    const url = new URL(req.url);
    const duration = url.searchParams.get("duration") || "30";
    
    const apiRes = await fetch(`${SUBMISSION_API_URL}/submissions/${id}/test/start?duration=${duration}`, {
      method: "POST",
    });

    if (!apiRes.ok) {
      const errText = await apiRes.text();
      return NextResponse.json({ error: errText || "Failed to trigger load test" }, { status: apiRes.status });
    }

    const data = await apiRes.json();
    return NextResponse.json(data);
  } catch (err: any) {
    return NextResponse.json({ error: err.message || "Internal server error" }, { status: 500 });
  }
}
