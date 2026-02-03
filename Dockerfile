FROM python:3.11-slim

# FFmpeg é necessário para render_worker
RUN apt-get update && apt-get install -y ffmpeg curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY workers/ ./workers/
COPY scripts/ ./scripts/
COPY config/ ./config/
COPY worker_runner.py .

ENV PORT=8080
EXPOSE 8080

CMD ["python", "worker_runner.py"]
