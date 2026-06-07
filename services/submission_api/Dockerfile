FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY shared /app/shared
COPY bots /app/bots
COPY services/submission_api /app/services/submission_api
COPY infra/seccomp_profile.json /app/infra/seccomp_profile.json
ENV PYTHONPATH=/app
EXPOSE 8000
CMD ["uvicorn", "services.submission_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
