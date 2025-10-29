#!/bin/bash

# Sentiment Analysis Dashboard - Quick Setup Script

echo "========================================="
echo "Sentiment Analysis Dashboard Setup"
echo "========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is installed
echo "Checking prerequisites..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker is not installed${NC}"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi
echo -e "${GREEN}✓ Docker is installed${NC}"

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}✗ Docker Compose is not installed${NC}"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose is installed${NC}"
echo ""

# Create necessary directories
echo "Creating directories..."
mkdir -p backend/core backend/routes backend/tests backend/scripts
mkdir -p frontend/src/components/Dashboard frontend/src/components/Auth frontend/src/components/Admin
mkdir -p frontend/public
mkdir -p nginx database models data logs
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo -e "${GREEN}✓ .env file created${NC}"
    echo -e "${YELLOW}⚠️  Please edit .env file with your configuration${NC}"
else
    echo -e "${YELLOW}⚠️  .env file already exists${NC}"
fi
echo ""

# Create __init__.py files
echo "Creating __init__.py files..."
touch backend/__init__.py
touch backend/core/__init__.py
touch backend/routes/__init__.py
touch backend/tests/__init__.py
echo -e "${GREEN}✓ __init__.py files created${NC}"
echo ""

# Build and start Docker containers
echo "Building Docker containers..."
docker-compose build
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Failed to build Docker containers${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker containers built${NC}"
echo ""

echo "Starting services..."
docker-compose up -d
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Failed to start services${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Services started${NC}"
echo ""

# Wait for database to be ready
echo "Waiting for database to be ready..."
sleep 10

# Initialize database
echo "Initializing database..."
docker-compose exec -T backend python scripts/init_db.py
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  Database initialization failed or already initialized${NC}"
else
    echo -e "${GREEN}✓ Database initialized${NC}"
fi
echo ""

# Seed database with sample data
echo "Seeding database with sample data..."
docker-compose exec -T backend python scripts/seed_data.py
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  Database seeding failed or already seeded${NC}"
else
    echo -e "${GREEN}✓ Database seeded${NC}"
fi
echo ""

echo "========================================="
echo -e "${GREEN}✓ Setup completed successfully!${NC}"
echo "========================================="
echo ""
echo "Services are running at:"
echo -e "  ${GREEN}Frontend:${NC} http://localhost:3000"
echo -e "  ${GREEN}Backend API:${NC} http://localhost:5000"
echo -e "  ${GREEN}Health Check:${NC} http://localhost:5000/health"
echo ""
echo "Demo Credentials:"
echo "  Admin: admin@sentimentdashboard.com / Admin@123"
echo "  Analyst: analyst@test.com / Test@123"
echo "  Viewer: viewer@test.com / Test@123"
echo ""
echo "Useful commands:"
echo "  docker-compose logs -f       # View logs"
echo "  docker-compose stop          # Stop services"
echo "  docker-compose restart       # Restart services"
echo "  docker-compose down          # Stop and remove containers"
echo ""