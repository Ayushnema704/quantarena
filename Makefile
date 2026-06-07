.PHONY: demo up down logs test integration lint sample-zip benchmark chaos sandbox-test

COMPOSE := docker compose
PYTHON := python3
VENV := .venv/bin

demo: up
	@echo "Platform running:"
	@echo "  Frontend:     http://localhost:3000"
	@echo "  Submit API:   http://localhost:8000/docs"
	@echo "  WS proxy:     ws://localhost:8787/ws/<id>"
	@echo "  Prometheus:   http://localhost:9090"
	@echo "  Ingester metrics: http://localhost:9100/metrics"

up:
	$(COMPOSE) up -d --build
	@$(PYTHON) scripts/wait_for_services.py || true

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

sample-zip:
	cd examples/sample_orderbook && zip -r ../sample_orderbook.zip . -x "*.pyc" -x "__pycache__/*"

real-zip:
	cd examples/real_matching_engine && zip -r ../real_matching_engine.zip . -x "*.pyc" -x "__pycache__/*"

test:
	PYTHONPATH=. $(VENV)/pytest tests/ -v --ignore=tests/integration/full_loop.py -m "not benchmark"

integration: sample-zip
	SKIP_DOCKER_TESTS=0 SKIP_INTEGRATION=0 PYTHONPATH=. $(VENV)/pytest tests/integration/full_loop.py tests/chaos/ -v -s

benchmark:
	PYTHONPATH=. $(VENV)/pytest tests/self_benchmark.py -v -m benchmark -s

chaos:
	@echo "Usage: make chaos SUBMISSION_ID=xxx WS_URL=ws://localhost:8787/ws/xxx"

sandbox-test:
	chmod +x scripts/sandbox_selftest.sh && ./scripts/sandbox_selftest.sh

lint:
	$(VENV)/ruff check services bots tests scripts shared 2>/dev/null || true

install:
	$(PYTHON) -m venv .venv
	$(VENV)/pip install -r requirements.txt
