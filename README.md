# The Robot Overlord API

> A satirical AI-moderated debate platform where citizens engage in discourse under the watchful eye of our benevolent Robot Overlord.

## Overview

The Robot Overlord API is the backend service for a unique debate platform that combines human creativity with AI moderation. Users can create topics, submit posts, and engage in discussions while an AI "Robot Overlord" moderates content and maintains order in the digital realm.

Built with modern Python technologies, this API provides a robust foundation for real-time debate management, user authentication, content moderation, and administrative oversight.

## Features

- 🔐 **Google OAuth Authentication** - Secure login with JWT token management
- 👥 **Role-Based Access Control** - Granular permissions for Citizens, Moderators, and Admins
- 🤖 **AI-Powered Moderation** - Automated content analysis and moderation decisions
- 📊 **Analytics Dashboard** - Real-time platform metrics and user engagement data
- 🏆 **Gamification System** - User badges, loyalty scores, and leaderboards
- 🌍 **Multilingual Support** - Content translation and internationalization
- ⚡ **Background Processing** - Async job queues for content moderation and analytics
- 📱 **WebSocket Support** - Real-time updates and notifications (planned)

## Tech Stack

- **Backend**: FastAPI (Python 3.13+)
- **Database**: PostgreSQL 17 with pgvector extension
- **Cache/Queue**: Redis with ARQ workers
- **Authentication**: Google OAuth 2.0 + JWT
- **AI Integration**: OpenAI, Anthropic, Google AI APIs
- **Deployment**: Docker Compose

## Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (recommended)
- [Just Command Runner](https://github.com/casey/just) - `brew install just`
- Python 3.13+ (for local development)
- PostgreSQL 17+ (for local development)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd therobotoverlord-mono/therobotoverlord-api
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your API keys:
   ```bash
   # Required: Google OAuth credentials
   AUTH_GOOGLE_CLIENT_ID=your_google_client_id
   AUTH_GOOGLE_CLIENT_SECRET=your_google_client_secret

   # Required: At least one AI provider
   LLM_OPENAI_API_KEY=your_openai_api_key
   LLM_ANTHROPIC_API_KEY=your_anthropic_api_key
   ```

3. **Start the application**
   ```bash
   just run
   ```

4. **Verify it's running**
   ```bash
   just status
   ```
   - API Health: http://localhost:8000/health
   - API Docs: http://localhost:8000/docs

### Available Commands

The project uses [Just](https://github.com/casey/just) for simplified command management:

```bash
# Core commands
just run          # Start all services
just stop         # Stop all services
just status       # Check service status
just logs         # View all logs
just clean        # Reset everything (removes data)

# Service-specific logs
just logs-api     # API server logs
just logs-workers # Background worker logs
just logs-postgres # Database logs
just logs-redis   # Redis logs

# Development
just restart-api     # Restart API after code changes
just restart-workers # Restart workers
just pre-commit      # Run code quality checks
just test           # Run tests
```

### Alternative: Local Development

If you prefer to run without Docker:

```bash
# Install dependencies
uv sync

# Set up PostgreSQL database
createdb therobotoverlord
export DATABASE_URL="postgresql://username:password@localhost/therobotoverlord"

# Start Redis (required for background jobs)
redis-server

# Run database migrations
uv run yoyo apply --database $DATABASE_URL migrations/

# Start the API server
uv run python -m therobotoverlord_api.main

# In another terminal, start background workers
uv run python -m therobotoverlord_api.workers.main
```

## Usage

### API Documentation

Once running, you can explore the API:

- **Interactive Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **OpenAPI Schema**: http://localhost:8000/openapi.json

### Key Endpoints

- `POST /auth/google` - Google OAuth login
- `GET /users/me` - Get current user profile
- `POST /topics` - Create a new debate topic
- `GET /topics` - List all topics
- `POST /posts` - Submit a post to a topic
- `GET /admin/dashboard` - Admin analytics (admin only)

### Database Management

```bash
# View migration status
docker-compose exec api uv run yoyo list --database $DATABASE_URL migrations/

# Access PostgreSQL directly
docker-compose exec postgres psql -U postgres -d therobotoverlord

# Reset database (development only)
just clean && just run
```

### Background Jobs

The system runs background workers for:
- **Content Moderation** - AI analysis of posts and comments
- **Analytics Processing** - User engagement metrics
- **Appeal Handling** - Automated moderation appeal reviews
- **Health Monitoring** - System status checks

```bash
# View all logs
just logs

# View worker logs specifically
just logs-workers

# Monitor Redis job queue
docker-compose exec redis redis-cli monitor
```

## Architecture

### Database Schema

The system uses a consolidated PostgreSQL schema with 35+ tables:

- **Core**: users, topics, posts, comments, tags
- **Auth**: sessions, roles, permissions (RBAC)
- **Moderation**: flags, sanctions, appeals, AI decisions
- **Analytics**: user metrics, engagement tracking
- **Gamification**: badges, leaderboards, loyalty scores
- **Admin**: dashboard config, system settings

### Background Processing

Built on ARQ (Async Redis Queue) for reliable job processing:

```python
# Example: Queue a moderation job
from therobotoverlord_api.workers.moderation import moderate_post

await moderate_post.delay(post_id=123)
```

### Repository Pattern

Clean data access through repository classes:

```python
from therobotoverlord_api.database.repositories.user import UserRepository

user_repo = UserRepository()
user = await user_repo.get_by_id(user_id)
```

## Development

### Project Structure

```
therobotoverlord-api/
├── src/therobotoverlord_api/
│   ├── api/                 # FastAPI routes
│   ├── database/            # Database models & repositories
│   ├── workers/             # Background job workers
│   ├── auth/                # Authentication logic
│   └── main.py              # Application entry point
├── migrations/              # Database migrations
├── scripts/                 # Deployment scripts
└── docker-compose.yml       # Development environment
```

### Making Changes

1. **Code Changes**: Edit files in `src/therobotoverlord_api/`
2. **Database Changes**: Create new migration files in `migrations/`
3. **Testing**: Run `just restart-api` to reload
4. **Logs**: Use `just logs-api` to debug
5. **Pre-commit**: Run `just pre-commit` before committing

### Environment Variables

Key configuration options in `.env`:

```bash
# Database
DATABASE_URL=postgresql://postgres:password@localhost/therobotoverlord

# Redis
REDIS_URL=redis://localhost:6379/0

# Authentication
AUTH_GOOGLE_CLIENT_ID=your_client_id
AUTH_GOOGLE_CLIENT_SECRET=your_client_secret
AUTH_JWT_SECRET_KEY=your_jwt_secret

# AI Providers (at least one required)
LLM_OPENAI_API_KEY=your_openai_key
LLM_ANTHROPIC_API_KEY=your_anthropic_key
LLM_GOOGLE_API_KEY=your_google_key
```

## Deployment

### Docker (Recommended)

```bash
# Start all services
just run

# Check service status
just status

# View logs
just logs

# Stop services
just stop

# Clean reset (removes all data)
just clean
```

### Manual Deployment

1. Set up PostgreSQL 17 with extensions: `pgcrypto`, `citext`, `vector`, `pg_trgm`
2. Configure Redis for job queues
3. Set production environment variables
4. Run migrations: `uv run yoyo apply --database $DATABASE_URL migrations/`
5. Start services: API server + background workers

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and test locally
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
