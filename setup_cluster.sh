#!/bin/bash

# TestCase Generation Platform - Complete Setup Script
# This script will:
# 1. Create Python virtual environment
# 2. Install required dependencies
# 3. Start Docker Compose cluster (x86 or arm compose file)
# 4. Wait for services to be ready
# 5. Initialize database schema
# 6. Display cluster status
#
# Usage: ./setup_cluster.sh [--platform x86|arm] [--recreate]

set -e

echo "🚀 TestCase Generation Platform - Complete Setup"
echo "=================================================="

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${GREEN}✅ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

ARCH_SUFFIX=""
RECREATE_DB=false

detect_platform() {
  case "$(uname -m)" in
    x86_64|amd64) ARCH_SUFFIX="x86" ;;
    aarch64|arm64) ARCH_SUFFIX="arm" ;;
    *)
      print_error "Unsupported architecture: $(uname -m). Use --platform x86 or --platform arm."
      exit 1
      ;;
  esac
}

while [[ $# -gt 0 ]]; do
  case $1 in
    --platform)
      case "$2" in
        x86|arm) ARCH_SUFFIX="$2" ;;
        *)
          print_error "Invalid platform: $2 (expected x86 or arm)"
          exit 1
          ;;
      esac
      shift 2
      ;;
    --recreate)
      RECREATE_DB=true
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [--platform x86|arm] [--recreate]"
      echo "  x86  Intel/AMD64 (docker-compose_cpu_standalone_x86.yml)"
      echo "  arm  Apple Silicon / ARM64 (docker-compose_cpu_standalone_arm.yml)"
      echo "  --recreate  Drop and recreate testcase_db schema (destructive)"
      echo "If --platform is omitted, architecture is auto-detected from uname -m."
      exit 0
      ;;
    *)
      print_error "Unknown option: $1"
      exit 1
      ;;
  esac
done

if [ -z "$ARCH_SUFFIX" ]; then
  detect_platform
  print_info "Auto-detected platform: $ARCH_SUFFIX"
fi

COMPOSE_FILE="docker-compose_cpu_standalone_${ARCH_SUFFIX}.yml"

if [ ! -f "$COMPOSE_FILE" ]; then
  print_error "Compose file not found: $COMPOSE_FILE"
  exit 1
fi

compose_cmd() {
  if docker compose version >/dev/null 2>&1; then
    docker compose -f "$COMPOSE_FILE" "$@"
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose -f "$COMPOSE_FILE" "$@"
  else
    print_error "Docker Compose is not installed."
    exit 1
  fi
}

if ! docker info > /dev/null 2>&1; then
  print_error "Docker is not running. Please start Docker Desktop first."
  exit 1
fi

print_info "Using compose file: $COMPOSE_FILE"
print_info "Starting setup process..."

print_info "Step 1: Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
  python3 -m venv venv
  print_status "Created Python virtual environment"
else
  print_warning "Virtual environment already exists, skipping creation"
fi

print_info "Step 2: Activating virtual environment..."
source venv/bin/activate
print_status "Virtual environment activated"

print_info "Step 3: Installing Python dependencies..."
pip install --upgrade pip
pip install psycopg2-binary
print_status "Python dependencies installed"

print_info "Step 4: Starting Docker Compose cluster..."
compose_cmd up -d
print_status "Docker Compose cluster started"

print_info "Step 5: Waiting for PostgreSQL to be ready..."
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
  if compose_cmd exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
    print_status "PostgreSQL is ready!"
    break
  else
    print_info "Waiting for PostgreSQL... (attempt $attempt/$max_attempts)"
    sleep 2
    ((attempt++))
  fi
done

if [ $attempt -gt $max_attempts ]; then
  print_error "PostgreSQL failed to start within expected time"
  exit 1
fi

print_info "Step 6: Waiting for database to be accessible..."
sleep 5

print_info "Step 7: Initializing database schema..."
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=testcase_db
export DB_USER=postgres
export DB_PASSWORD=password

if [ "$RECREATE_DB" = true ]; then
  print_warning "Recreating database schema (all testcase_db data will be deleted)..."
  python3 init_versioning_db.py --recreate
else
  python3 init_versioning_db.py
fi

if [ $? -eq 0 ]; then
  print_status "Database initialization completed successfully!"
else
  print_error "Database initialization failed"
  exit 1
fi

print_info "Step 8: Checking cluster status..."

echo ""
echo "🎉 Setup Complete! Cluster Status:"
echo "=================================="
compose_cmd ps

echo ""
print_info "🌐 Access your application at: http://localhost"
print_info "🔐 Keycloak Admin: http://localhost:8090"
print_info "📊 RabbitMQ Management: http://localhost:15672"
print_info "🗄️  Neo4j Browser: http://localhost:7474"
print_info "🔍 Weaviate: http://localhost:8082"

echo ""
print_status "Setup completed successfully! 🚀"
print_info "To stop the cluster later, run: docker compose -f $COMPOSE_FILE down"
print_info "To reactivate the environment, run: source venv/bin/activate"
