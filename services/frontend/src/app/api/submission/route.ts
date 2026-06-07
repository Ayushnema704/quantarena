import { NextResponse } from "next/server";

const SUBMISSION_API_URL = process.env.SUBMISSION_API_URL ?? "http://localhost:8000";

export async function POST(req: Request) {
  try {
    const formData = await req.formData();
    const file = formData.get("file");
    if (!file) {
      return NextResponse.json({ error: "No file provided" }, { status: 400 });
    }

    const apiFormData = new FormData();
    apiFormData.append("file", file);

    const apiRes = await fetch(`${SUBMISSION_API_URL}/submit`, {
      method: "POST",
      body: apiFormData,
    });

    if (!apiRes.ok) {
      const errText = await apiRes.text();
      return NextResponse.json({ error: errText || "Failed to submit code" }, { status: apiRes.status });
    }

    const data = await apiRes.json();
    return NextResponse.json(data);
  } catch (err: any) {
    return NextResponse.json({ error: err.message || "Internal server error" }, { status: 500 });
  }
}
