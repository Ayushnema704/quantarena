FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" websockets
COPY services/ws_proxy/main.py /app/main.py
EXPOSE 8787
ENV WS_PROXY_PORT=8787
CMD ["python", "main.py"]
