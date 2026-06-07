import { fetchLeaderboard } from "@/lib/redis";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(request: Request) {
  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      const send = (data: unknown) => {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(data)}\n\n`));
      };

      const tick = async () => {
        try {
          const entries = await fetchLeaderboard();
          const top = entries[0];
          send({
            type: "leaderboard",
            entries,
            p50: top?.p50_us ?? 0,
            p90: top?.p90_us ?? 0,
            p99: top?.p99_us ?? 0,
            ts: Date.now(),
          });
        } catch (e) {
          send({ type: "error", message: String(e) });
        }
      };

      await tick();
      const interval = setInterval(tick, 1000);

      request.signal.addEventListener("abort", () => {
        clearInterval(interval);
        controller.close();
      });
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}
