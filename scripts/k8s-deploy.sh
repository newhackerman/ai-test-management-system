#!/bin/bash

# Kubernetes Deployment Script for AI Test Management System
# Usage: ./scripts/k8s-deploy.sh [environment]

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT=${1:-production}
NAMESPACE="ai-test-management"

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
    
    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed. Please install kubectl first."
        exit 1
    fi
    
    # Check if kubectl can connect to cluster
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster. Please check your kubeconfig."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Create namespace
create_namespace() {
    log_info "Creating namespace..."
    
    kubectl apply -f "$PROJECT_ROOT/k8s/namespace.yaml"
    
    log_success "Namespace created/updated"
}

# Apply configurations
apply_configs() {
    log_info "Applying configurations..."
    
    # Apply ConfigMaps
    kubectl apply -f "$PROJECT_ROOT/k8s/configmap.yaml"
    
    # Apply Secrets (WARNING: Update these in production!)
    kubectl apply -f "$PROJECT_ROOT/k8s/secrets.yaml"
    
    log_success "Configurations applied"
}

# Deploy databases
deploy_databases() {
    log_info "Deploying databases..."
    
    # Deploy MySQL
    kubectl apply -f "$PROJECT_ROOT/k8s/mysql-deployment.yaml"
    
    # Deploy Redis
    kubectl apply -f "$PROJECT_ROOT/k8s/redis-deployment.yaml"
    
    # Wait for databases to be ready
    log_info "Waiting for databases to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/mysql -n $NAMESPACE
    kubectl wait --for=condition=available --timeout=300s deployment/redis -n $NAMESPACE
    
    log_success "Databases deployed successfully"
}

# Deploy applications
deploy_applications() {
    log_info "Deploying applications..."
    
    # Deploy backend
    kubectl apply -f "$PROJECT_ROOT/k8s/backend-deployment.yaml"
    
    # Deploy frontend
    kubectl apply -f "$PROJECT_ROOT/k8s/frontend-deployment.yaml"
    
    # Wait for applications to be ready
    log_info "Waiting for applications to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/backend -n $NAMESPACE
    kubectl wait --for=condition=available --timeout=300s deployment/frontend -n $NAMESPACE
    
    log_success "Applications deployed successfully"
}

# Setup ingress
setup_ingress() {
    log_info "Setting up ingress..."
    
    kubectl apply -f "$PROJECT_ROOT/k8s/ingress.yaml"
    
    log_success "Ingress configured"
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."
    
    # Get a backend pod
    BACKEND_POD=$(kubectl get pods -n $NAMESPACE -l app=backend -o jsonpath='{.items[0].metadata.name}')
    
    if [ -n "$BACKEND_POD" ]; then
        kubectl exec -n $NAMESPACE $BACKEND_POD -- alembic upgrade head
        log_success "Database migrations completed"
    else
        log_error "No backend pod found for running migrations"
        return 1
    fi
}

# Health check
health_check() {
    log_info "Performing health check..."
    
    # Check if all deployments are ready
    if kubectl get deployments -n $NAMESPACE | grep -q "0/"; then
        log_error "Some deployments are not ready"
        kubectl get deployments -n $NAMESPACE
        return 1
    fi
    
    log_success "All deployments are healthy"
}

# Show status
show_status() {
    log_info "Deployment status:"
    
    echo ""
    echo "Namespace: $NAMESPACE"
    echo ""
    
    echo "Deployments:"
    kubectl get deployments -n $NAMESPACE
    echo ""
    
    echo "Services:"
    kubectl get services -n $NAMESPACE
    echo ""
    
    echo "Ingress:"
    kubectl get ingress -n $NAMESPACE
    echo ""
    
    echo "Pods:"
    kubectl get pods -n $NAMESPACE
}

# Main deployment function
main() {
    log_info "Starting Kubernetes deployment for environment: $ENVIRONMENT"
    
    check_prerequisites
    create_namespace
    apply_configs
    deploy_databases
    
    # Wait a bit for databases to initialize
    sleep 30
    
    deploy_applications
    run_migrations
    setup_ingress
    health_check
    show_status
    
    log_success "Kubernetes deployment completed successfully!"
    log_info "Your application should be available at the configured ingress hosts"
}

# Handle script interruption
trap 'log_error "Deployment interrupted"; exit 1' INT TERM

# Run main function
main "$@"