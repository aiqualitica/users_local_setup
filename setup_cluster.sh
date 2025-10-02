#!/bin/bash

# TestCase Generation Platform - Complete Setup Script
# This script will:
# 1. Create Python virtual environment
# 2. Install required dependencies
# 3. Start Docker Compose cluster
# 4. Wait for services to be ready
# 5. Initialize database schema
# 6. Display cluster status

set -e  # Exit on any error

echo "🚀 TestCase Generation Platform - Complete Setup"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker Desktop first."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

print_info "Starting setup process..."

# Step 1: Create Python virtual environment
print_info "Step 1: Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_status "Created Python virtual environment"
else
    print_warning "Virtual environment already exists, skipping creation"
fi

# Step 2: Activate virtual environment
print_info "Step 2: Activating virtual environment..."
source venv/bin/activate
print_status "Virtual environment activated"

# Step 3: Install required Python packages
print_info "Step 3: Installing Python dependencies..."
pip install --upgrade pip
pip install psycopg2-binary
print_status "Python dependencies installed"

# Step 4: Navigate to deployment directory
print_info "Step 4: Using current directory for Docker Compose..."
# We're already in the users_local_setup directory with the docker-compose file

# Step 5: Start Docker Compose cluster
print_info "Step 5: Starting Docker Compose cluster..."
docker-compose -f docker-compose_cpu_standalone.yml up -d

print_status "Docker Compose cluster started"

# Step 6: Wait for PostgreSQL to be ready
print_info "Step 6: Waiting for PostgreSQL to be ready..."
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if docker-compose -f docker-compose_cpu_standalone.yml exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
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

# Step 7: Wait for database to be accessible
print_info "Step 7: Waiting for database to be accessible..."
sleep 5

# Step 8: Run database initialization script
print_info "Step 8: Initializing database schema..."
# The init script is in the current directory

# Set environment variables for the script
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=testcase_db
export DB_USER=postgres
export DB_PASSWORD=password

python3 init_versioning_db.py

if [ $? -eq 0 ]; then
    print_status "Database initialization completed successfully!"
else
    print_error "Database initialization failed"
    exit 1
fi

# Step 9: Check cluster status
print_info "Step 9: Checking cluster status..."
# We're already in the correct directory

echo ""
echo "🎉 Setup Complete! Cluster Status:"
echo "=================================="
docker-compose -f docker-compose_cpu_standalone.yml ps

echo ""
print_info "🌐 Access your application at: http://localhost"
print_info "📊 RabbitMQ Management: http://localhost:15672"
print_info "🗄️  Neo4j Browser: http://localhost:7474"
print_info "🔍 Qdrant Dashboard: http://localhost:6333/dashboard"

echo ""
print_status "Setup completed successfully! 🚀"
print_info "To stop the cluster later, run: docker-compose -f docker-compose_cpu_standalone.yml down"
print_info "To reactivate the environment, run: source venv/bin/activate"
