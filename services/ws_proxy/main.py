"""WebSocket edge proxy — bridges default network (bots) to isolated contestant_net."""
from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager

import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

UPSTREAMS: dict[str, str] = {}


class RegisterRequest(BaseModel):
    submission_id: str
    upstream_host: str
    upstream_port: int = 8765


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield


app = FastAPI(title="QuantArena WS Edge Proxy", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "upstreams": len(UPSTREAMS)}


@app.post("/register")
async def register(req: RegisterRequest):
    url = f"ws://{req.upstream_host}:{req.upstream_port}"
    UPSTREAMS[req.submission_id] = url
    return {"submission_id": req.submission_id, "ws_path": f"/ws/{req.submission_id}"}


@app.delete("/register/{submission_id}")
async def unregister(submission_id: str):
    UPSTREAMS.pop(submission_id, None)
    return {"removed": submission_id}


@app.websocket("/ws/{submission_id}")
async def proxy_ws(client: WebSocket, submission_id: str):
    upstream_url = UPSTREAMS.get(submission_id)
    if not upstream_url:
        await client.close(code=4404)
        return
    await client.accept()
    try:
        async with websockets.connect(upstream_url) as upstream:
            async def client_to_upstream():
                try:
                    while True:
                        data = await client.receive_text()
                        await upstream.send(data)
                except WebSocketDisconnect:
                    pass

            async def upstream_to_client():
                async for msg in upstream:
                    if isinstance(msg, bytes):
                        await client.send_bytes(msg)
                    else:
                        await client.send_text(msg)

            t1 = asyncio.create_task(client_to_upstream())
            t2 = asyncio.create_task(upstream_to_client())
            done, pending = await asyncio.wait(
                [t1, t2],
                return_when=asyncio.FIRST_COMPLETED
            )
            for t in pending:
                t.cancel()
    except Exception:
        await client.close(code=1011)


def main() -> None:
    import uvicorn

    port = int(os.environ.get("WS_PROXY_PORT", "8787"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
