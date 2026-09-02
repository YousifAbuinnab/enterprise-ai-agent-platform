FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffering stdout/stderr (cleaner container logs)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first so this layer is cached unless requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code after dependencies for better layer caching
COPY app/ ./app/

# Run as a non-root user for defense-in-depth
RUN useradd --create-home appuser && \
    mkdir -p /app/uploads && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
