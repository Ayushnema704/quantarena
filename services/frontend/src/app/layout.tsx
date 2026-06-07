import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "QuantArena Platform — Leaderboard",
  description: "Latency measurement and sandboxing platform for quantitative trading matching engines",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
