"use client";

import Link from "next/link";
import type { LeaderboardEntry } from "@/lib/redis";

type Props = { entries: LeaderboardEntry[] };

function statusClass(s: string) {
  if (s === "running") return "status live";
  if (s === "completed") return "status done";
  if (s === "failed") return "status fail";
  return "status idle";
}

export function LeaderboardTable({ entries }: Props) {
  if (entries.length === 0) {
    return <p style={{ color: "var(--muted)" }}>No submissions yet.</p>;
  }
  return (
    <section className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Name</th>
            <th>Status</th>
            <th>Final</th>
            <th>Spd</th>
            <th>RPS</th>
            <th>Cor</th>
            <th>Stb</th>
            <th>p99 µs</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((e, i) => (
            <tr key={e.id}>
              <td className="rank mono">{i + 1}</td>
              <td>
                <Link href={`/submission/${e.id}`}>{e.name}</Link>
              </td>
              <td>
                <span className={statusClass(e.test_status)}>{e.test_status}</span>
              </td>
              <td className="score mono">{e.score.toFixed(1)}</td>
              <td className="mono">{e.speed_score.toFixed(0)}</td>
              <td className="mono">{e.throughput_score.toFixed(0)}</td>
              <td className="mono">{e.correctness_score.toFixed(0)}</td>
              <td className="mono">{e.stability_score.toFixed(0)}</td>
              <td className="mono">{e.p99_us.toFixed(0)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
