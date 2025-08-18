# The Robot Overlord API

A satirical AI-moderated debate platform API built with FastAPI and PostgreSQL.

## Features

- **Google OAuth Authentication** - Secure user authentication with JWT tokens
- **Role-based Access Control** - Citizen, Moderator, Admin, Super Admin roles
- **Session Management** - Refresh token rotation with reuse detection
- **User Management** - Profile creation, loyalty scoring, leaderboards
- Topic creation and management (planned)
- Post submission and moderation (planned)
- Real-time queue visualization (planned)
- Private messaging (planned)
- Appeals and reporting system (planned)

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL 17 with asyncpg
- **Authentication**: Google OAuth 2.0 + JWT
- **Session Storage**: PostgreSQL (user_sessions table)
- **Queue System**: PostgreSQL-based queues
- **AI Integration**: Planned (OpenAI GPT for Overlord moderation)

## Development Setup

### Prerequisites

- Python 3.13+
- PostgreSQL 17+
- Google OAuth 2.0 credentials

### Installation

1. Clone the repository:
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
