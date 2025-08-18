# The Robot Overlord API

FastAPI backend for The Robot Overlord debate platform.

## Database Setup

### Prerequisites

- Docker and Docker Compose
- Python 3.13+
- PostgreSQL client tools (optional, for direct database access)

### Quick Start

1. **Start the database services:**
   ```bash
   docker-compose up -d
   ```

2. **Install dependencies:**
   ```bash
   uv sync --dev
   ```

3. **Run database migrations:**
   ```bash
   # Set environment variable for local development
   export DATABASE_URL="postgresql://postgres:password@localhost:5432/therobotoverlord"

   # Run migrations
   cd migrations
   yoyo apply --database $DATABASE_URL
   ```

4. **Verify database setup:**
   ```python
   # Test the database connection
   python -c "
   import asyncio
   from src.therobotoverlord_api.database.health import health_checker

   async def test():
       result = await health_checker.full_health_check()
       print(result)

   asyncio.run(test())
   "
   ```

### Database Configuration

The database can be configured via environment variables:

- `DATABASE_URL` - Full PostgreSQL connection string
- `DATABASE_MIN_POOL_SIZE` - Minimum connection pool size (default: 5)
- `DATABASE_MAX_POOL_SIZE` - Maximum connection pool size (default: 20)
- `DATABASE_POOL_TIMEOUT` - Connection pool timeout in seconds (default: 30)

### Migration Management

Migrations are managed using `yoyo-migrations`:

```bash
# Apply all pending migrations
yoyo apply --database $DATABASE_URL

# Rollback last migration
yoyo rollback --database $DATABASE_URL

# Show migration status
yoyo list --database $DATABASE_URL

# Create new migration
yoyo new --database $DATABASE_URL -m "Description of changes"
```

### Database Schema

The database includes:

- **Core Tables**: users, topics, posts, tags
- **Queue System**: topic_creation_queue, post_moderation_queue, private_message_queue
- **Governance**: appeals, flags, sanctions
- **Gamification**: badges, user_badges
- **Event Sourcing**: moderation_events
- **Multilingual**: translations
- **Performance**: materialized views and strategic indexes

### Health Checks

The API includes comprehensive database health checks:

```python
from therobotoverlord_api.database.health import health_checker

# Basic connection check
await health_checker.check_connection()

# Full system health check
await health_checker.full_health_check()
```

### Development Database

For local development, use the provided Docker Compose setup:

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f postgres

# Stop services
docker-compose down

# Reset database (WARNING: destroys all data)
docker-compose down -v
docker-compose up -d
```

### Production Deployment

For production on Render.com:

1. Create a PostgreSQL 17 database with extensions enabled
2. Set the `DATABASE_URL` environment variable
3. Run migrations during deployment
4. Monitor health checks via the API endpoints

## Repository Pattern

The API uses a repository pattern for database access:

```python
from therobotoverlord_api.database.repositories.user import UserRepository

# Create repository instance
user_repo = UserRepository()

# Basic operations
user = await user_repo.get_by_id(user_id)
users = await user_repo.get_all(limit=50)
new_user = await user_repo.create_user(user_data)
```

## Connection Management

Database connections are managed through a connection pool:

```python
from therobotoverlord_api.database.connection import get_db_connection, get_db_transaction

# Get a connection
async with get_db_connection() as conn:
    result = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)

# Get a transaction
async with get_db_transaction() as conn:
    await conn.execute("INSERT INTO users (...) VALUES (...)")
    await conn.execute("INSERT INTO moderation_events (...) VALUES (...)")
    # Automatically commits on success, rolls back on exception
```
