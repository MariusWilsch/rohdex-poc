FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.7.1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    EMAIL_POLLING_ENABLED=true

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install "poetry==$POETRY_VERSION"

# Copy poetry configuration files
COPY pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry install --no-dev --no-root

# Create necessary directories
RUN mkdir -p /app/logs /app/context

# Copy project
COPY . .

# Add openpyxl for Excel processing
RUN pip install openpyxl

# Expose the port the app runs on
EXPOSE 8000

# Create a non-root user to run the app
RUN adduser --disabled-password --gecos "" appuser
RUN chown -R appuser:appuser /app
USER appuser

# Entry point - modify to bind to all interfaces
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000"] 