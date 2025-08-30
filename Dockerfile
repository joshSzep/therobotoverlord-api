# Use Python 3.13 slim image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    postgresql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python package management
RUN pip install uv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY migrations/ ./migrations/

# Install Python dependencies
RUN uv sync --frozen

# Make startup script executable
RUN chmod +x /app/scripts/start_api.sh

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["/app/scripts/start_api.sh"]
