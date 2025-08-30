# The Robot Overlord API - Docker Setup Guide

This guide will help you run the complete backend system using Docker Compose with the consolidated migration approach.

## Prerequisites

1. **Docker Desktop** - Make sure Docker Desktop is installed and running
2. **Just Command Runner** - Install `just` for simplified commands: `brew install just`
3. **API Keys** - Update the `.env` file with your actual API keys (see Configuration section)

## Quick Start

1. **Start Docker Desktop** (if not already running)

2. **Configure Environment Variables**
   ```bash
   # Copy and edit the environment file
   cp .env.example .env
   # Edit .env with your actual API keys and configuration
   ```

3. **Build and Start Services (Recommended)**
   ```bash
   # Using just command (recommended)
   just run

   # Or using docker-compose directly
   docker-compose up --build -d
   ```

4. **Check Service Health**
   ```bash
   # Using just command
   just status

   # Or manually
   docker-compose ps
   curl http://localhost:8000/health
   ```

5. **View Logs**
   ```bash
   # Using just command
   just logs

   # Or using docker-compose
   docker-compose logs -f
   ```

## Services Overview

The Docker Compose setup includes:

- **postgres** - PostgreSQL database with pgvector extension (port 5432)
- **redis** - Redis for caching and job queues (port 6379)
- **api** - FastAPI application server (port 8000)
- **workers** - Background task workers for content moderation

## Configuration

### Required API Keys

Update these values in `.env`:

```bash
# Authentication
AUTH_GOOGLE_CLIENT_ID=your_actual_google_client_id
AUTH_GOOGLE_CLIENT_SECRET=your_actual_google_client_secret
AUTH_JWT_SECRET_KEY=your_secure_jwt_secret_key

# LLM Providers (at least one required)
LLM_ANTHROPIC_API_KEY=your_anthropic_api_key
LLM_OPENAI_API_KEY=your_openai_api_key
LLM_GOOGLE_API_KEY=your_google_api_key
```

### Database Migrations

**Consolidated Migration Approach**: The system now uses a single consolidated migration file (`001_initial_schema.sql`) that contains the complete database schema. This eliminates dependency conflicts and ensures consistent deployments.

Database migrations run automatically when the API service starts. The startup script:

1. Waits for PostgreSQL to be ready
2. Waits for Redis to be ready
3. Runs the consolidated migration using yoyo
4. Starts the FastAPI server

**Migration Features**:
- Complete schema with 35+ tables
- RBAC (Role-Based Access Control) system
- Content moderation and appeals system
- Loyalty scoring and leaderboard system
- Badge and tag systems
- Admin dashboard capabilities

## API Endpoints

Once running, the API will be available at:

- **Health Check**: `http://localhost:8000/health`
- **API Documentation**: `http://localhost:8000/docs`
- **WebSocket**: `ws://localhost:8000/ws`

## Development Workflow

### Making Code Changes

The API service mounts your source code as a volume, so changes are reflected immediately:

```bash
# Restart just the API service after code changes
docker-compose restart api

# Restart workers after worker code changes
docker-compose restart workers
```

### Database Operations

```bash
# Access PostgreSQL directly
docker-compose exec postgres psql -U postgres -d therobotoverlord

# View migration status
docker-compose exec api uv run yoyo list --database $DATABASE_URL migrations/

# Reset database (WARNING: destroys all data)
docker-compose down -v
docker-compose up --build -d

# Manual migration (if needed)
docker-compose exec api uv run yoyo apply --database $DATABASE_URL migrations/
```

### Redis Operations

```bash
# Access Redis CLI
docker-compose exec redis redis-cli

# Monitor Redis operations
docker-compose exec redis redis-cli monitor
```

## Troubleshooting

### Service Won't Start

```bash
# Check service status
docker-compose ps

# View detailed logs
docker-compose logs [service-name]

# Rebuild specific service
docker-compose up --build [service-name]
```

### Database Connection Issues

```bash
# Check if PostgreSQL is ready
docker-compose exec postgres pg_isready -U postgres

# Check database logs
docker-compose logs postgres
```

### API Health Check Fails

```bash
# Check API logs
docker-compose logs api

# Test database connection from API container
docker-compose exec api uv run python -c "
from therobotoverlord_api.database.connection import init_database
import asyncio
asyncio.run(init_database())
print('Database connection successful')
"
```

### Worker Issues

```bash
# Check worker logs
docker-compose logs workers

# Restart workers
docker-compose restart workers
```

## Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: destroys data)
docker-compose down -v

# Stop and remove images
docker-compose down --rmi all
```

## Production Considerations

Before deploying to production:

1. **Security**: Update all default passwords and secrets
2. **SSL**: Configure SSL certificates for HTTPS
3. **Environment**: Use production-grade environment variables
4. **Monitoring**: Add logging and monitoring solutions
5. **Backup**: Set up database backup strategies
6. **Scaling**: Consider using Docker Swarm or Kubernetes

## Network Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   Frontend      │────│   API Service   │
│  (port 3000)    │    │   (port 8000)   │
└─────────────────┘    └─────────────────┘
                              │
                    ┌─────────┼─────────┐
                    │                   │
            ┌───────▼────────┐ ┌────────▼────────┐
            │  PostgreSQL    │ │     Redis       │
            │  (port 5432)   │ │  (port 6379)    │
            └────────────────┘ └─────────────────┘
                    │                   │
            ┌───────▼────────┐ ┌────────▼────────┐
            │   Migrations   │ │   Worker Pool   │
            │   (automatic)  │ │  (background)   │
            └────────────────┘ └─────────────────┘
```
