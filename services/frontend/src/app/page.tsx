"use client";

import { useEffect, useState } from "react";
import { LeaderboardTable } from "@/components/LeaderboardTable";
import { P99Chart } from "@/components/P99Chart";
import { CodeUploadWizard } from "@/components/CodeUploadWizard";
import type { LeaderboardEntry } from "@/lib/redis";

export default function HomePage() {
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [latencyHistory, setLatencyHistory] = useState<{ ts: number; p50?: number; p90?: number; p99?: number }[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const es = new EventSource("/api/stream");
    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);
    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.type === "leaderboard" && Array.isArray(data.entries)) {
          setEntries(data.entries);
          const p50 = Number(data.p50 ?? 0);
          const p90 = Number(data.p90 ?? 0);
          const p99 = Number(data.p99 ?? 0);
          if (p99 > 0) {
            setLatencyHistory((prev) => {
              const next = [...prev, { ts: data.ts ?? Date.now(), p50, p90, p99 }];
              return next.slice(-120);
            });
          }
        }
      } catch {
        /* ignore */
      }
    };
    return () => es.close();
  }, []);

  return (
    <div className="container">
      <header>
        <h1>QuantArena Platform</h1>
        <p>
          Sandboxed submissions · HdrHistogram percentiles · Live leaderboard{" "}
          <span className={`status ${connected ? "live" : "idle"}`}>
            {connected ? "LIVE" : "CONNECTING"}
          </span>
        </p>
      </header>

      <CodeUploadWizard />
      <LeaderboardTable entries={entries} />
      <P99Chart data={latencyHistory} />
    </div>
  );
}
