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

# Drop the database if it exists
PGPASSWORD=${DATABASE_PASSWORD:-password} dropdb -h ${DATABASE_HOST:-localhost} -p ${DATABASE_PORT:-5432} -U ${DATABASE_USERNAME:-postgres} therobotoverlord || true

# Create database if it doesn't exist
PGPASSWORD=${DATABASE_PASSWORD:-password} createdb -h ${DATABASE_HOST:-localhost} -p ${DATABASE_PORT:-5432} -U ${DATABASE_USERNAME:-postgres} therobotoverlord || true

# Run database migrations
echo "Running database migrations..."
cd /app
uv run yoyo apply --database "postgresql://${DATABASE_USERNAME:-postgres}:${DATABASE_PASSWORD:-password}@${DATABASE_HOST:-localhost}:${DATABASE_PORT:-5432}/therobotoverlord" migrations/

# Start the API server
echo "Starting API server..."
exec uv run python -m therobotoverlord_api.main
