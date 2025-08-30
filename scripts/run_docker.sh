#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker Desktop and try again."
        exit 1
    fi
    print_success "Docker is running"
}

# Check if .env file exists
check_env_file() {
    if [ ! -f ".env" ]; then
        print_warning ".env file not found. Creating from .env.example..."
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_warning "Please update .env with your actual API keys before running the services"
        else
            print_error ".env.example not found. Cannot create .env file."
            exit 1
        fi
    else
        print_success ".env file found"
    fi
}

# Main execution
main() {
    print_status "Starting The Robot Overlord API with Docker Compose..."

    # Pre-flight checks
    check_docker
    check_env_file

    # Stop any existing containers
    print_status "Stopping existing containers..."
    docker-compose down --remove-orphans || true

    # Build and start services
    print_status "Building and starting services..."
    docker-compose up --build -d

    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 10

    # Check service health
    print_status "Checking service health..."

    # Check if containers are running
    if docker-compose ps | grep -q "Up"; then
        print_success "Services are running"

        # Test API health endpoint
        print_status "Testing API health endpoint..."
        for i in {1..30}; do
            if curl -s http://localhost:8000/health >/dev/null 2>&1; then
                print_success "API is healthy and responding"
                break
            elif [ $i -eq 30 ]; then
                print_warning "API health check timeout. Check logs with: docker-compose logs api"
            else
                echo -n "."
                sleep 2
            fi
        done

        echo ""
        print_success "The Robot Overlord API is now running!"
        echo ""
        echo "🚀 Services:"
        echo "   • API Server:     http://localhost:8000"
        echo "   • API Docs:       http://localhost:8000/docs"
        echo "   • Health Check:   http://localhost:8000/health"
        echo "   • PostgreSQL:     localhost:5432"
        echo "   • Redis:          localhost:6379"
        echo ""
        echo "📋 Useful commands:"
        echo "   • View logs:      docker-compose logs -f"
        echo "   • Stop services:  docker-compose down"
        echo "   • Restart API:    docker-compose restart api"
        echo "   • Check status:   docker-compose ps"
        echo ""

    else
        print_error "Some services failed to start. Check logs with: docker-compose logs"
        docker-compose ps
        exit 1
    fi
}

# Run main function
main "$@"
