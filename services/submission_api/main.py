"""Submission API — POST /submit accepts zip, builds image, runs sandboxed container."""
from __future__ import annotations

import asyncio
import os
import socket
from contextlib import asynccontextmanager
from pathlib import Path

import docker
import httpx
import redis.asyncio as redis
from docker.errors import DockerException, NotFound
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel
from pydantic_settings import BaseSettings

from services.submission_api.builder import SubmissionBuildError, prepare_submission
from services.submission_api.sandbox import SANDBOX_CONFIG, container_kwargs, verify_runtime


class Settings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    build_dir: str = "/tmp/iicpc-builds"
    ws_proxy_url: str = "http://ws_proxy:8787"
    ws_public_host: str = "localhost"
    ws_public_port: int = 8787

    class Config:
        env_file = ".env"


settings = Settings(
    redis_url=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
    build_dir=os.environ.get("BUILD_DIR", "/tmp/iicpc-builds"),
    ws_proxy_url=os.environ.get("WS_PROXY_URL", "http://localhost:8787"),
    ws_public_host=os.environ.get("WS_PUBLIC_HOST", "localhost"),
    ws_public_port=int(os.environ.get("WS_PUBLIC_PORT", "8787")),
)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


async def _register_ws_proxy(submission_id: str, host: str, port: int = 8765) -> str:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{settings.ws_proxy_url}/register",
            json={"submission_id": submission_id, "upstream_host": host, "upstream_port": port},
        )
        resp.raise_for_status()
    return f"ws://{settings.ws_public_host}:{settings.ws_public_port}/ws/{submission_id}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = redis.from_url(settings.redis_url, decode_responses=True)
    Path(settings.build_dir).mkdir(parents=True, exist_ok=True)
    try:
        app.state.docker = docker.from_env()
        app.state.runtime_info = verify_runtime(app.state.docker)
    except DockerException:
        app.state.docker = None
        app.state.runtime_info = {"docker": "unavailable"}
    yield
    await app.state.redis.aclose()


app = FastAPI(title="QuantArena Submission API", lifespan=lifespan)


class SubmitResponse(BaseModel):
    submission_id: str
    ws_url: str
    container_id: str
    image_tag: str
    sandbox_runtime: str


class SubmissionStatus(BaseModel):
    submission_id: str
    status: str
    ws_url: str | None
    test_status: str | None = None


@app.get("/health")
async def health():
    return {"status": "ok", "sandbox": getattr(app.state, "runtime_info", {})}


@app.post("/submit", response_model=SubmitResponse)
async def submit(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(400, "upload must be a .zip file")
    if app.state.docker is None:
        raise HTTPException(503, "docker unavailable")

    data = await file.read()
    build_root = Path(settings.build_dir)

    try:
        submission_id, _project_dir, tag = prepare_submission(data, build_root)
    except SubmissionBuildError as e:
        raise HTTPException(400, str(e)) from e

    container_name = f"iicpc-{submission_id}"
    client = app.state.docker

    try:
        try:
            old = client.containers.get(container_name)
            old.remove(force=True)
        except NotFound:
            pass

        use_isolated = SANDBOX_CONFIG["network_mode"] == "contestant_net"
        host_port = _free_port() if not use_isolated else None
        kwargs = container_kwargs(
            tag,
            container_name,
            network="contestant_net" if use_isolated else "bridge",
            publish_port=host_port,
        )
        container = client.containers.run(**kwargs)
        container.reload()

        if use_isolated:
            nets = container.attrs.get("NetworkSettings", {}).get("Networks", {})
            contestant_ip = nets.get("contestant_net", {}).get("IPAddress")
            if not contestant_ip:
                raise HTTPException(503, "contestant container has no IP on contestant_net")
            ws_url_host = await _register_ws_proxy(submission_id, contestant_ip)
        else:
            ws_url_host = f"ws://127.0.0.1:{host_port}"
    except DockerException as e:
        raise HTTPException(503, f"failed to start container: {e}") from e
    except httpx.HTTPError as e:
        raise HTTPException(503, f"ws proxy registration failed: {e}") from e

    name = file.filename.replace(".zip", "")
    await app.state.redis.hset(
        f"submission:{submission_id}",
        mapping={
            "status": "running",
            "test_status": "ready",
            "ws_url": ws_url_host,
            "container_id": container.id,
            "image_tag": tag,
            "name": name,
        },
    )

    return SubmitResponse(
        submission_id=submission_id,
        ws_url=ws_url_host,
        container_id=container.id,
        image_tag=tag,
        sandbox_runtime=SANDBOX_CONFIG["runtime"],
    )


@app.get("/submissions/{submission_id}", response_model=SubmissionStatus)
async def get_submission(submission_id: str):
    data = await app.state.redis.hgetall(f"submission:{submission_id}")
    if not data:
        raise HTTPException(404, "submission not found")
    return SubmissionStatus(
        submission_id=submission_id,
        status=data.get("status", "unknown"),
        ws_url=data.get("ws_url"),
        test_status=data.get("test_status"),
    )


async def run_load_test_task(submission_id: str, ws_url: str, duration: float = 30.0):
    try:
        from bots.limit_order_bot import LimitOrderBot
        # Rewrite ws_url from host perspective (localhost) to internal docker perspective (ws_proxy)
        internal_ws_url = ws_url.replace("localhost", "ws_proxy").replace("127.0.0.1", "ws_proxy")
        
        bot = LimitOrderBot(
            ws_url=internal_ws_url,
            submission_id=submission_id,
            redis_url=settings.redis_url,
            interval_ns=10_000_000,  # 10ms interval = 100 RPS
            bot_id="web-bot-0",
        )
        
        # Run the bot
        await bot.run(duration)
        
        # Mark test as completed
        await app.state.redis.hset(f"submission:{submission_id}", "test_status", "completed")
    except Exception as e:
        print(f"Error running load test for {submission_id}: {e}")
        await app.state.redis.hset(f"submission:{submission_id}", "test_status", "failed")


@app.post("/submissions/{submission_id}/test/start")
async def start_test(submission_id: str, duration: float = 30.0):
    data = await app.state.redis.hgetall(f"submission:{submission_id}")
    if not data:
        raise HTTPException(404, "submission not found")
    
    ws_url = data.get("ws_url")
    if not ws_url:
        raise HTTPException(400, "WebSocket URL not found for submission")
        
    await app.state.redis.hset(f"submission:{submission_id}", "test_status", "running")
    
    # Spawn background load test task
    asyncio.create_task(run_load_test_task(submission_id, ws_url, duration))
    
    return {"test_status": "running", "ws_url": ws_url}


@app.post("/submissions/{submission_id}/test/complete")
async def complete_test(submission_id: str, failed: bool = False):
    status = "failed" if failed else "completed"
    await app.state.redis.hset(f"submission:{submission_id}", "test_status", status)
    return {"test_status": status}


@app.delete("/submissions/{submission_id}")
async def stop_submission(submission_id: str):
    data = await app.state.redis.hgetall(f"submission:{submission_id}")
    if not data:
        raise HTTPException(404, "submission not found")
    cid = data.get("container_id")
    if cid and app.state.docker:
        try:
            app.state.docker.containers.get(cid).remove(force=True)
        except (DockerException, NotFound):
            pass
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.delete(f"{settings.ws_proxy_url}/register/{submission_id}")
    except httpx.HTTPError:
        pass
    await app.state.redis.hset(
        f"submission:{submission_id}",
        mapping={"status": "stopped", "test_status": "stopped"},
    )
    return {"status": "stopped"}
