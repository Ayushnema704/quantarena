FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt aiohttp
COPY shared /app/shared
COPY services/ingester /app/services/ingester
ENV PYTHONPATH=/app
EXPOSE 9100
CMD ["python", "-m", "services.ingester.main"]
