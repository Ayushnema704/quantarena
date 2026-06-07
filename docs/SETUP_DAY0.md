# Day 0 setup checklist

Run on your Mac before `make demo`:

1. **Docker Desktop** — [Install](https://docs.docker.com/desktop/setup/install/mac-install/), then:
   ```bash
   docker run hello-world
   ```

2. **gVisor (optional Week 1, required Week 2)**
   ```bash
   # https://gvisor.dev/docs/user_guide/install/
   docker run --runtime=runsc hello-world
   ```
   Set `DOCKER_RUNTIME=runsc` in `.env`.

3. **Python 3.11+** — `python3 --version`

4. **Node 20+** — `node --version`

5. **GitHub** — create private repo `iicpc-platform`, push this tree.

6. **Oracle Cloud / Fly.io** — accounts for Week 2 distributed bots.

7. **Bookmarks** — Gil Tene latency talk, HdrHistogram docs, gVisor security model, Locust distributed mode, Timescale hypertables.
