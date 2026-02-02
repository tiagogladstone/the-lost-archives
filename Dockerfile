FROM python:3.11-slim

# Install FFmpeg
RUN apt-get update && apt-get install -y ffmpeg curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy scripts and config
COPY scripts/ ./scripts/
COPY config/ ./config/

# Copy main entry point
COPY main.py .

# Cloud Run uses PORT env var
ENV PORT=8080
EXPOSE 8080

CMD ["python", "main.py"]
