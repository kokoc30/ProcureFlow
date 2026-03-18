FROM python:3.11-slim

WORKDIR /app

# Install dependencies first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (structure must match path resolution in backend/utils/settings.py)
COPY backend/ backend/
COPY frontend/ frontend/
COPY shared/ shared/

# Default port for local Docker; Render overrides via PORT env var
ENV PORT=8000

EXPOSE ${PORT}

# Shell form so $PORT is expanded at runtime
CMD uvicorn backend.main:app --host 0.0.0.0 --port $PORT
