FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# OpenCV needs these
RUN apt-get update && apt-get install -y --no-install-recommends \
      libgl1 libglib2.0-0 ffmpeg curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Pre-fetch YOLO weights at build time so first run is instant.
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

CMD ["python", "-m", "app.main"]
