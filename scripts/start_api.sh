#!/bin/bash
set -e

echo "Starting The Robot Overlord API..."

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

# Run database migrations
echo "Running database migrations..."
cd /app
uv run yoyo apply --database "${DATABASE_URL}" migrations/

# Start the API server
echo "Starting API server..."
exec uv run python -m therobotoverlord_api.main
