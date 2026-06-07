"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { P99Chart } from "@/components/P99Chart";

type Snapshot = {
  name?: string;
  p50_us?: number;
  p90_us?: number;
  p99_us?: number;
  p50_intended_us?: number;
  p90_intended_us?: number;
  p99_intended_us?: number;
  speed_score?: number;
  throughput_score?: number;
  correctness_score?: number;
  stability_score?: number;
  composite_score?: number;
  error_rate?: number;
  fill_match_rate?: number;
  test_status?: string;
  rps?: number;
};

export default function SubmissionDetailPage() {
  const params = useParams();
  const id = String(params.id);
  const [snap, setSnap] = useState<Snapshot | null>(null);
  const [history, setHistory] = useState<{ ts: number; p99: number }[]>([]);
  const [testing, setTesting] = useState(false);
  const [testDuration, setTestDuration] = useState(30);
  const [testError, setTestError] = useState<string | null>(null);

  const loadData = async () => {
    const [sRes, hRes] = await Promise.all([
      fetch(`/api/submission/${id}`),
      fetch(`/api/submission/${id}/history`),
    ]);
    if (sRes.ok) setSnap(await sRes.json());
    if (hRes.ok) {
      const h = await hRes.json();
      setHistory(h.points ?? []);
    }
  };

  useEffect(() => {
    loadData();
    const t = setInterval(loadData, 2000);
    return () => clearInterval(t);
  }, [id]);

  const triggerTest = async () => {
    setTesting(true);
    setTestError(null);
    try {
      const res = await fetch(`/api/submission/${id}?duration=${testDuration}`, {
        method: "POST",
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || "Failed to trigger load test");
      }
      // Instantly refresh status
      await loadData();
    } catch (err: any) {
      setTestError(err.message || "An unexpected error occurred.");
    } finally {
      setTesting(false);
    }
  };

  return (
    <main className="container">
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: "1.5rem" }}>
        <div>
          <p>
            <Link href="/">← Leaderboard</Link>
          </p>
          <h1 style={{ marginTop: "0.5rem" }}>{snap?.name ?? id}</h1>
          <p>
            Test Status:{" "}
            <span className={`status ${snap?.test_status === "running" ? "live" : snap?.test_status === "completed" ? "done" : snap?.test_status === "failed" ? "fail" : "idle"}`}>
              {snap?.test_status ?? "unknown"}
            </span>
          </p>
        </div>

        <div style={{ display: "flex", gap: "1rem", alignItems: "center", marginBottom: "0.5rem", flexWrap: "wrap" }}>
          <div className="form-group" style={{ margin: 0 }}>
            <select
              value={testDuration}
              onChange={(e) => setTestDuration(Number(e.target.value))}
              disabled={snap?.test_status === "running" || testing}
              style={{ background: "#0f132a", border: "1px solid var(--border)", color: "#fff", padding: "0.5rem", borderRadius: "6px" }}
            >
              <option value={10}>10s Duration</option>
              <option value={30}>30s Duration</option>
              <option value={60}>60s Duration</option>
            </select>
          </div>
          <button
            className="btn-primary"
            onClick={triggerTest}
            disabled={snap?.test_status === "running" || testing}
            style={{ padding: "0.5rem 1rem", fontSize: "0.9rem", boxShadow: "none" }}
          >
            {snap?.test_status === "running" ? "Testing Running..." : testing ? "Launching..." : "Trigger New Load Test"}
          </button>
        </div>
      </header>

      {testError && (
        <div className="error-message" style={{ marginBottom: "2rem" }}>
          {testError}
        </div>
      )}

      <section className="detail-grid">
        <article className="stat-card">
          <h3>Composite Score</h3>
          <p className="mono big">{(snap?.composite_score ?? 0).toFixed(1)}</p>
        </article>
        <article className="stat-card">
          <h3>Speed / Throughput / Correctness / Stability</h3>
          <p className="mono">
            {(snap?.speed_score ?? 0).toFixed(0)} / {(snap?.throughput_score ?? 0).toFixed(0)} /{" "}
            {(snap?.correctness_score ?? 0).toFixed(0)} / {(snap?.stability_score ?? 0).toFixed(0)}
          </p>
        </article>
        <article className="stat-card">
          <h3>Actual p50 / p90 / p99 (µs)</h3>
          <p className="mono">
            {(snap?.p50_us ?? 0).toFixed(0)} / {(snap?.p90_us ?? 0).toFixed(0)} /{" "}
            {(snap?.p99_us ?? 0).toFixed(0)}
          </p>
        </article>
        <article className="stat-card">
          <h3>Intended p99 (µs)</h3>
          <p className="mono">{(snap?.p99_intended_us ?? 0).toFixed(0)}</p>
        </article>
        <article className="stat-card">
          <h3>Fill match / Error rate</h3>
          <p className="mono">
            {((snap?.fill_match_rate ?? 0) * 100).toFixed(1)}% /{" "}
            {((snap?.error_rate ?? 0) * 100).toFixed(2)}%
          </p>
        </article>
        <article className="stat-card">
          <h3>Sustained RPS</h3>
          <p className="mono big">{(snap?.rps ?? 0).toFixed(1)}</p>
        </article>
      </section>

      <P99Chart data={history} />
    </main>
  );
}
