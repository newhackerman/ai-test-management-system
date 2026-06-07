#!/bin/bash

# AI Test Management System Deployment Script
# Usage: ./scripts/deploy.sh [environment] [version]

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT=${1:-production}
VERSION=${2:-latest}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if environment file exists
    if [ ! -f "$PROJECT_ROOT/backend/.env.$ENVIRONMENT" ]; then
        log_error "Environment file .env.$ENVIRONMENT not found."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Backup database
backup_database() {
    if [ "$ENVIRONMENT" = "production" ]; then
        log_info "Creating database backup..."
        
        BACKUP_DIR="$PROJECT_ROOT/backups"
        mkdir -p "$BACKUP_DIR"
        
        BACKUP_FILE="$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).sql"
        
        docker-compose -f "$PROJECT_ROOT/backend/docker-compose.yml" exec mysql \
            mysqldump -u root -p"${MYSQL_ROOT_PASSWORD}" ai_test_db > "$BACKUP_FILE"
        
        log_success "Database backup created: $BACKUP_FILE"
    fi
}

# Pull latest images
pull_images() {
    log_info "Pulling latest Docker images..."
    
    cd "$PROJECT_ROOT/backend"
    docker-compose --env-file ".env.$ENVIRONMENT" pull
    
    log_success "Docker images pulled successfully"
}

# Build images
build_images() {
    log_info "Building Docker images..."
    
    cd "$PROJECT_ROOT/backend"
    docker-compose --env-file ".env.$ENVIRONMENT" build --no-cache
    
    log_success "Docker images built successfully"
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."
    
    cd "$PROJECT_ROOT/backend"
    docker-compose --env-file ".env.$ENVIRONMENT" run --rm backend \
        alembic upgrade head
    
    log_success "Database migrations completed"
}

# Deploy services
deploy_services() {
    log_info "Deploying services..."
    
    cd "$PROJECT_ROOT/backend"
    
    # Stop existing services
    docker-compose --env-file ".env.$ENVIRONMENT" down
    
    # Start services
    if [ "$ENVIRONMENT" = "production" ]; then
        docker-compose --env-file ".env.$ENVIRONMENT" --profile production up -d
    else
        docker-compose --env-file ".env.$ENVIRONMENT" --profile development up -d
    fi
    
    log_success "Services deployed successfully"
}

# Health check
health_check() {
    log_info "Performing health check..."
    
    # Wait for services to start
    sleep 30
    
    # Check backend health
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log_success "Backend service is healthy"
    else
        log_error "Backend service health check failed"
        return 1
    fi
    
    # Check frontend health
    if curl -f http://localhost:3000/health > /dev/null 2>&1; then
        log_success "Frontend service is healthy"
    else
        log_error "Frontend service health check failed"
        return 1
    fi
    
    log_success "All services are healthy"
}

# Cleanup old images
cleanup() {
    log_info "Cleaning up old Docker images..."
    
    docker image prune -f
    docker volume prune -f
    
    log_success "Cleanup completed"
}

# Main deployment function
main() {
    log_info "Starting deployment for environment: $ENVIRONMENT, version: $VERSION"
    
    check_prerequisites
    
    if [ "$ENVIRONMENT" = "production" ]; then
        backup_database
    fi
    
    if [ "$VERSION" = "latest" ]; then
        build_images
    else
        pull_images
    fi
    
    run_migrations
    deploy_services
    health_check
    cleanup
    
    log_success "Deployment completed successfully!"
    log_info "Services are available at:"
    log_info "  - Frontend: http://localhost:3000"
    log_info "  - Backend API: http://localhost:8000"
    log_info "  - API Documentation: http://localhost:8000/docs"
    
    if [ "$ENVIRONMENT" = "development" ]; then
        log_info "  - phpMyAdmin: http://localhost:8080"
        log_info "  - Redis Commander: http://localhost:8081"
    fi
}

# Handle script interruption
trap 'log_error "Deployment interrupted"; exit 1' INT TERM

# Run main function
main "$@"