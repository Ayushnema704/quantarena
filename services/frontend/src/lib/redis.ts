import { createClient, type RedisClientType } from "redis";

const REDIS_URL = process.env.REDIS_URL ?? "redis://localhost:6379/0";

let client: RedisClientType | null = null;

export async function getRedis(): Promise<RedisClientType> {
  if (!client) {
    client = createClient({ url: REDIS_URL });
    client.on("error", (err) => console.error("Redis error", err));
    await client.connect();
  }
  return client;
}

export const LEADERBOARD_KEY = "leaderboard";

export type LeaderboardEntry = {
  id: string;
  name: string;
  p50_us: number;
  p90_us: number;
  p99_us: number;
  rps: number;
  event_count: number;
  score: number;
  speed_score: number;
  throughput_score: number;
  correctness_score: number;
  stability_score: number;
  test_status: string;
  error_rate: number;
  fill_match_rate: number;
};

export async function fetchLeaderboard(): Promise<LeaderboardEntry[]> {
  const r = await getRedis();
  const raw = await r.zRangeWithScores(LEADERBOARD_KEY, 0, -1, { REV: true });
  return raw.map((item, idx) => {
    let parsed: Record<string, unknown> = {};
    try {
      parsed = JSON.parse(item.value);
    } catch {
      parsed = { name: item.value };
    }
    return {
      id: String(parsed.id ?? idx),
      name: String(parsed.name ?? "unknown"),
      p50_us: Number(parsed.p50_us ?? 0),
      p90_us: Number(parsed.p90_us ?? 0),
      p99_us: Number(parsed.p99_us ?? 0),
      rps: Number(parsed.rps ?? 0),
      event_count: Number(parsed.event_count ?? 0),
      score: item.score,
      speed_score: Number(parsed.speed_score ?? 0),
      throughput_score: Number(parsed.throughput_score ?? 0),
      correctness_score: Number(parsed.correctness_score ?? 0),
      stability_score: Number(parsed.stability_score ?? 0),
      test_status: String(parsed.test_status ?? "unknown"),
      error_rate: Number(parsed.error_rate ?? 0),
      fill_match_rate: Number(parsed.fill_match_rate ?? 1),
    };
  });
}

export async function fetchSubmissionSnapshot(
  submissionId: string,
): Promise<Record<string, unknown> | null> {
  const r = await getRedis();
  const raw = await r.get(`snapshot:latest:${submissionId}`);
  if (!raw) return null;
  return JSON.parse(raw);
}

export type LatencyHistoryPoint = {
  ts: number;
  p50: number;
  p90: number;
  p99: number;
};

export async function fetchLatencyHistory(
  submissionId: string,
  limit = 120,
): Promise<LatencyHistoryPoint[]> {
  const dbUrl = process.env.DATABASE_URL;
  if (!dbUrl) return [];
  const { Pool } = await import("pg");
  const pool = new Pool({ connectionString: dbUrl });
  try {
    const res = await pool.query(
      `SELECT extract(epoch from time)*1000 as ts, p50_us as p50, p90_us as p90, p99_us as p99
       FROM latency_snapshots
       WHERE submission_id = $1
       ORDER BY time DESC
       LIMIT $2`,
      [submissionId, limit],
    );
    return res.rows.reverse().map((row: { ts: string; p50: string; p90: string; p99: string }) => ({
      ts: Number(row.ts),
      p50: Number(row.p50),
      p90: Number(row.p90),
      p99: Number(row.p99),
    }));
  } finally {
    await pool.end();
  }
}
