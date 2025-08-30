#!/bin/bash
set -e

# Wait for database to be ready
echo "Waiting for database to be ready..."
until pg_isready -h ${DATABASE_HOST:-localhost} -p ${DATABASE_PORT:-5432} -U ${DATABASE_USERNAME:-postgres}; do
  echo "Database is unavailable - sleeping"
  sleep 2
done
echo "Database is up - continuing"

# Wait for Redis to be ready
echo "Waiting for Redis to be ready..."
until redis-cli -h ${REDIS_HOST:-localhost} -p ${REDIS_PORT:-6379} ping; do
  echo "Redis is unavailable - sleeping"
  sleep 2
done
echo "Redis is up - continuing"

# Start the workers
echo "Starting background workers..."
cd /app
exec uv run python scripts/start_workers.py
