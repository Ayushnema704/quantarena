"""Minimal WebSocket orderbook echo server — contestant test fixture (~50 lines)."""
import asyncio
import json
import time

import websockets


async def handler(ws):
    async for raw in ws:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            await ws.send(json.dumps({"error": "invalid_json"}))
            continue
        ack = {
            "type": "ack",
            "order_id": msg.get("order_id"),
            "side": msg.get("side"),
            "price": msg.get("price"),
            "qty": msg.get("qty"),
            "ack_ts_ns": time.time_ns(),
            "received_ts_ns": time.time_ns(),
        }
        await ws.send(json.dumps(ack))


async def main():
    async with websockets.serve(handler, "0.0.0.0", 8765):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
