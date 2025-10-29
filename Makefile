.PHONY: help install setup start stop restart logs clean test

help:
	@echo "Sentiment Analysis Dashboard - Make Commands"
	@echo ""
	@echo "Setup Commands:"
	@echo "  make install     - Install all dependencies"
	@echo "  make setup       - Initial project setup"
	@echo "  make init-db     - Initialize database"
	@echo "  make seed        - Seed database with sample data"
	@echo ""
	@echo "Docker Commands:"
	@echo "  make start       - Start all services"
	@echo "  make stop        - Stop all services"
	@echo "  make restart     - Restart all services"
	@echo "  make logs        - View logs"
	@echo "  make build       - Build Docker images"
	@echo ""
	@echo "Development Commands:"
	@echo "  make dev         - Run in development mode"
	@echo "  make test        - Run tests"
	@echo "  make lint        - Run linters"
	@echo "  make clean       - Clean up files"

install:
	@echo "Installing backend dependencies..."
	cd backend && pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	cd frontend && npm install
	@echo "✓ Dependencies installed"

setup:
	@echo "Setting up project..."
	cp .env.example .env
	@echo "✓ Environment file created"
	@echo "⚠️  Please edit .env with your configuration"

init-db:
	@echo "Initializing database..."
	cd backend && python scripts/init_db.py
	@echo "✓ Database initialized"

seed:
	@echo "Seeding database..."
	cd backend && python scripts/seed_data.py
	@echo "✓ Database seeded"

start:
	@echo "Starting services..."
	docker-compose up -d
	@echo "✓ Services started"
	@echo "  Frontend: http://localhost:3000"
	@echo "  Backend:  http://localhost:5000"

stop:
	@echo "Stopping services..."
	docker-compose down
	@echo "✓ Services stopped"

restart:
	@echo "Restarting services..."
	docker-compose restart
	@echo "✓ Services restarted"

logs:
	docker-compose logs -f

build:
	@echo "Building Docker images..."
	docker-compose build
	@echo "✓ Images built"

dev:
	@echo "Starting development servers..."
	cd backend && python app.py &
	cd frontend && npm start

test:
	@echo "Running tests..."
	cd backend && pytest tests/ -v
	@echo "✓ Tests completed"

clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.log" -delete
	rm -rf backend/.pytest_cache
	@echo "✓ Cleanup completed"

