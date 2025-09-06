
# List available commands
help:
    @just --list

# Run the complete backend system with Docker Compose
run:
    @./scripts/run_docker.sh

# Stop all Docker services
stop:
    @docker-compose down

# View logs from all services
logs:
    @docker-compose logs -f

# View logs from a specific service (e.g., just logs-api)
logs-api:
    @docker-compose logs -f api

logs-workers:
    @docker-compose logs -f workers

logs-postgres:
    @docker-compose logs -f postgres

logs-redis:
    @docker-compose logs -f redis

# Check status of all services
status:
    @docker-compose ps

# Restart a specific service
restart-api:
    @docker-compose restart api

restart-workers:
    @docker-compose restart workers

# Clean up everything (WARNING: removes volumes and data)
clean:
    @docker-compose down -v --rmi all

# Run pre-commit hooks
pre-commit:
    @./scripts/pre-commit.sh

# Run tests
test:
    @./scripts/test.sh
