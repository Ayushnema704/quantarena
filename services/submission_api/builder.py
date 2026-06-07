"""Unzip submission, generate Dockerfile, build contestant image."""
from __future__ import annotations

import io
import shutil
import uuid
import zipfile
from pathlib import Path

import docker
from docker.errors import BuildError as DockerBuildError
from docker.errors import DockerException

DOCKERFILE_TEMPLATE = """FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt* ./
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi
COPY . .
EXPOSE 8765
CMD ["python", "server.py"]
"""


class SubmissionBuildError(Exception):
    pass


def extract_zip(zip_bytes: bytes, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        zf.extractall(dest)
    # If single top-level folder, use it as root
    children = [p for p in dest.iterdir() if p.name != "__MACOSX"]
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return dest


def ensure_dockerfile(project_dir: Path) -> None:
    dockerfile = project_dir / "Dockerfile"
    if not dockerfile.exists():
        dockerfile.write_text(DOCKERFILE_TEMPLATE)
    if not (project_dir / "server.py").exists():
        raise SubmissionBuildError("submission must contain server.py")


def build_image(project_dir: Path, tag: str) -> str:
    ensure_dockerfile(project_dir)
    try:
        client = docker.from_env()
        image, _ = client.images.build(path=str(project_dir), tag=tag, rm=True)
        return image.id
    except DockerBuildError as e:
        raise SubmissionBuildError(f"docker build failed: {e}") from e
    except DockerException as e:
        raise SubmissionBuildError(f"docker unavailable: {e}") from e


def prepare_submission(zip_bytes: bytes, build_root: Path) -> tuple[str, Path, str]:
    submission_id = str(uuid.uuid4())[:8]
    project_dir = build_root / submission_id
    if project_dir.exists():
        shutil.rmtree(project_dir)
    root = extract_zip(zip_bytes, project_dir)
    tag = f"iicpc/contestant:{submission_id}"
    build_image(root, tag)
    return submission_id, root, tag
