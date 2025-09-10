# Makefile for ka-chat-bot project
# Handles backend setup, virtual environment, uv configuration, and dependencies

# Load environment variables from .env file
include .env
export

# Variables
UV := $(shell command -v uv 2> /dev/null)
VENV_DIR := .venv
PYTHON := python3

# Phony targets
.PHONY: help setup install dev run start stop clean lint format check-deps build-frontend env-setup check-env db-setup db-schema-setup deploy

# Default target
help:
	@echo "Available targets:"
	@echo "  setup      - Complete project setup (install uv, create venv, install deps)"
	@echo "  install    - Install all dependencies"
	@echo "  dev        - Run development server"
	@echo "  run        - Run production server"
	@echo "  start      - Start both servers with log monitoring (recommended)"
	@echo "  stop       - Stop running servers"
	@echo "  clean      - Clean up generated files"
	@echo "  lint       - Run linting"
	@echo "  format     - Format code"
	@echo "  check-deps - Check for outdated dependencies"
	@echo "  build-frontend - Build frontend"
	@echo "  env-setup  - Setup environment variables"
	@echo "  check-env  - Check environment configuration"
	@echo "  db-setup   - Setup PostgreSQL database configuration"
	@echo "  db-schema-setup - Setup database schema with roles and permissions"
	@echo "  deploy     - Deploy the application using sh.deploy.sh"

# Complete setup - install uv, create venv, install deps
setup: install-uv install env-setup
	@echo "✅ Project setup complete!"
	@echo ""
	@echo "🎉 Setup complete! Next steps:"
	@echo "  1. Edit .env file with your Databricks configuration"
	@echo "  2. Run 'make build-frontend' to build the frontend"
	@echo "  3. Run 'make dev' to start the development server"

# Install uv package manager
install-uv:
ifndef UV
	@echo "📦 Installing uv package manager..."
	curl -LsSf https://astral.sh/uv/install.sh | sh
	@echo "✅ uv installed successfully"
else
	@echo "✅ uv is already installed"
endif

# Install backend dependencies using uv
install-backend:
	@echo "🐍 Setting up Python virtual environment with uv..."
	uv venv $(VENV_DIR)
	uv pip install -r requirements.txt
	@echo "✅ Backend dependencies installed"

# Install frontend dependencies
install-frontend:
	@echo "📦 Installing frontend dependencies..."
	cd frontend && npm install
	@echo "✅ Frontend dependencies installed"

# Install all dependencies
install: install-backend install-frontend
	@echo "✅ All dependencies installed"

# Run development server
dev: check-env
	@echo "🚀 Starting development server..."
	.venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run production server
run: check-env
	@echo "🚀 Starting production server..."
	.venv/bin/gunicorn main:app -w 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Stop running servers
stop:
	@echo "🛑 Stopping running servers..."
	@tmux kill-session -t ka-chat-bot 2>/dev/null || true
	@pkill -f "uvicorn main:app" || true
	@pkill -f "react-scripts start" || true
	@pkill -f "npm start" || true
	@echo "✅ Servers stopped"

# Clean up generated files
clean:
	@echo "🧹 Cleaning up..."
	rm -rf $(VENV_DIR)
	rm -rf frontend/node_modules
	rm -rf frontend/build-chat-app
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf .coverage
	@echo "✅ Cleanup complete"

# Run linting
lint:
	@echo "🔍 Running linting..."
	.venv/bin/ruff check .

# Format code
format:
	@echo "🎨 Formatting code..."
	.venv/bin/ruff format .

# Check for outdated dependencies
check-deps:
	@echo "📋 Checking for outdated dependencies..."
	uv pip list --outdated

# Build frontend
build-frontend:
	@echo "🔨 Building frontend..."
	cd frontend && npm run build
	@echo "✅ Frontend build complete"


# Check environment configuration
check-env:
	@echo "🔍 Checking environment configuration..."
	@if [ ! -f .env ]; then \
		echo "❌ .env file not found. Run 'make env-setup' first."; \
		exit 1; \
	fi
	@echo "✅ .env file exists"
	@if [ -z "$$LOCAL_API_TOKEN" ]; then \
		echo "⚠️  LOCAL_API_TOKEN not set in .env file"; \
	else \
		echo "✅ LOCAL_API_TOKEN is configured"; \
	fi
	@if [ -z "$$DATABRICKS_HOST" ]; then \
		echo "⚠️  DATABRICKS_HOST not set in .env file"; \
	else \
		echo "✅ DATABRICKS_HOST is configured"; \
	fi
	@if [ -z "$$SERVING_ENDPOINT_NAME" ]; then \
		echo "⚠️  SERVING_ENDPOINT_NAME not set in .env file"; \
	else \
		echo "✅ SERVING_ENDPOINT_NAME is configured"; \
	fi

# Database setup and configuration
db-setup:
	@echo "🗄️  Setting up PostgreSQL database configuration..."
	@if [ ! -f .env ]; then \
		echo "❌ .env file not found. Run 'make env-setup' first."; \
		exit 1; \
	fi
	@echo "📝 Add the following to your .env file:"
	@echo "   DB_USERNAME=your-username@databricks.com"
	@echo "   DB_INSTANCE_NAME=your-instance-name"
	@echo "   CLIENT_ID=your-client-id"
	@echo "   CLIENT_SECRET=your-client-secret"
	@echo ""
	@echo "🔗 Get these values from your Databricks workspace:"
	@echo "   - DB_USERNAME: Your Databricks username"
	@echo "   - DB_INSTANCE_NAME: Your database instance name"
	@echo "   - CLIENT_ID & CLIENT_SECRET: From Databricks OAuth app"

# Setup database schema with proper roles and permissions
db-schema-setup:
	@echo "🏗️ Setting up database schema with roles and permissions..."
	.venv/bin/python utils/setup_database_schema.py

# Deploy the application
deploy:
	@echo "🚀 Deploying application..."
	@if [ -f "deploy.sh" ]; then \
		chmod +x deploy.sh && sh deploy.sh; \
	else \
		echo "❌ sh.deploy.sh not found"; \
		exit 1; \
	fi
