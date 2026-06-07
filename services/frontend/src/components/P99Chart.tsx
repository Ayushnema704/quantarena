"use client";

import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
} from "recharts";

type Point = { ts: number; p50?: number; p90?: number; p99?: number };

type Props = {
  data: Point[];
};

export function P99Chart({ data }: Props) {
  const formatted = data.map((d) => ({
    ...d,
    label: new Date(d.ts).toLocaleTimeString(),
  }));

  return (
    <div className="chart-wrap">
      <h2 style={{ margin: "0 0 0.75rem", fontSize: "0.875rem", color: "var(--muted)" }}>
        Live Latency Percentiles (µs)
      </h2>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={formatted}>
          <XAxis dataKey="label" stroke="#7d8fa3" fontSize={11} tickLine={false} />
          <YAxis stroke="#7d8fa3" fontSize={11} tickLine={false} width={60} />
          <Tooltip
            contentStyle={{
              background: "#121820",
              border: "1px solid #1e2a3a",
              borderRadius: 6,
              fontFamily: "monospace",
            }}
          />
          <Legend wrapperStyle={{ fontSize: 11, paddingTop: 10 }} />
          <Line
            type="monotone"
            dataKey="p50"
            stroke="#06b6d4"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
            name="p50"
          />
          <Line
            type="monotone"
            dataKey="p90"
            stroke="#f59e0b"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
            name="p90"
          />
          <Line
            type="monotone"
            dataKey="p99"
            stroke="#10b981"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
            name="p99"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
