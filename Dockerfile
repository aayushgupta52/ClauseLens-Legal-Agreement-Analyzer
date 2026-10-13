# Build the React frontend first.
FROM node:20-bookworm-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Run the FastAPI backend and serve the built React app from the same origin.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

# Tesseract supports OCR for text-scanned documents when the app uses it.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-hin \
    tesseract-ocr-mar \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY configs/ ./configs/
COPY docs/ ./docs/
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Install runtime dependencies and the optional OCR libraries. No training/data downloads here.
RUN python -m pip install --upgrade pip \
    && python -m pip install ".[ocr]"

EXPOSE 10000
CMD ["sh", "-c", "python scripts/serve.py --host 0.0.0.0 --port ${PORT:-10000}"]
