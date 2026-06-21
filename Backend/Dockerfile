# syntax=docker/dockerfile:1

FROM python:3.11-slim

# ── System dependencies for OpenCV (and friends like Ultralytics/EasyOCR) ──
# libgl1            -> provides libGL.so.1   (the one currently crashing you)
# libglib2.0-0      -> provides libgthread/libglib used by cv2's GUI/video bits
# libsm6/libxext6/libxrender1 -> common X11 libs cv2 dlopen()s even headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python dependencies ──
# Copy just requirements first so Docker can cache this layer between builds
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application code ──
COPY . .

# Railway injects PORT at runtime; default to 8000 for local docker run
ENV PORT=8000
EXPOSE 8000

# api.py defines `app = FastAPI(...)` and lives at the repo root of this
# build context (i.e. this Dockerfile sits next to api.py, detectors/,
# main.py, analytics/, evidence/, requirements.txt).
CMD ["sh", "-c", "uvicorn api.api:app --host 0.0.0.0 --port ${PORT}"]
