#!/bin/bash

# =============================================================================
# TG-Ticket-Agent Development Environment Setup Script
# =============================================================================
# This script sets up the development environment for the TG-Ticket-Agent
# multi-agent Telegram bot for selling event tickets via Bill24/TixGear platform.
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# =============================================================================
# Prerequisites Check
# =============================================================================
print_header "Checking Prerequisites"

# Check Python
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    print_success "Python 3 found: $PYTHON_VERSION"
else
    print_error "Python 3 not found. Please install Python 3.11+"
    exit 1
fi

# Check Node.js
if command_exists node; then
    NODE_VERSION=$(node --version)
    print_success "Node.js found: $NODE_VERSION"
else
    print_error "Node.js not found. Please install Node.js 18+"
    exit 1
fi

# Check npm
if command_exists npm; then
    NPM_VERSION=$(npm --version)
    print_success "npm found: $NPM_VERSION"
else
    print_error "npm not found. Please install npm"
    exit 1
fi

# Check Docker
if command_exists docker; then
    DOCKER_VERSION=$(docker --version)
    print_success "Docker found: $DOCKER_VERSION"
else
    print_warning "Docker not found. Docker is required for production deployment."
fi

# Check Docker Compose
if command_exists docker-compose || docker compose version >/dev/null 2>&1; then
    print_success "Docker Compose found"
else
    print_warning "Docker Compose not found. Required for production deployment."
fi

# =============================================================================
# Environment Setup
# =============================================================================
print_header "Setting Up Environment"

# Create .env file if not exists
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_success "Created .env from .env.example"
        print_warning "Please update .env with your actual configuration values"
    else
        print_warning ".env.example not found. Creating basic .env file..."
        cat > .env << EOF
# =============================================================================
# TG-Ticket-Agent Environment Configuration
# =============================================================================

# Application
PORT=3000
DEBUG=true
ENV=development

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/tg_ticket_agent
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=tg_ticket_agent

# Redis
REDIS_URL=redis://localhost:6379/0

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_WEBHOOK_URL=https://your-domain.com/api/webhooks/telegram

# Bill24 API
BILL24_TEST_URL=https://api.bil24.pro:8443/json
BILL24_REAL_URL=https://api.bil24.pro/json
BILL24_DEFAULT_ZONE=test

# Admin Panel
ADMIN_JWT_SECRET=your-secret-key-change-in-production
ADMIN_JWT_EXPIRES_IN=24h
ADMIN_DEFAULT_USERNAME=admin
ADMIN_DEFAULT_PASSWORD=changeme123

# Webhooks
N8N_WEBHOOK_URL=
EOF
        print_success "Created basic .env file"
        print_warning "Please update .env with your actual configuration values"
    fi
else
    print_success ".env file already exists"
fi

# =============================================================================
# Backend Setup (Python/FastAPI)
# =============================================================================
print_header "Setting Up Backend (Python)"

# Create virtual environment if not exists
if [ ! -d "backend/venv" ]; then
    print_success "Creating Python virtual environment..."
    cd backend 2>/dev/null || mkdir -p backend && cd backend
    python3 -m venv venv
    cd ..
    print_success "Virtual environment created"
else
    print_success "Virtual environment already exists"
fi

# Activate virtual environment and install dependencies
if [ -f "backend/requirements.txt" ]; then
    print_success "Installing Python dependencies..."
    cd backend
    source venv/bin/activate || source venv/Scripts/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    deactivate
    cd ..
    print_success "Python dependencies installed"
else
    print_warning "backend/requirements.txt not found. Skipping Python dependency installation."
fi

# =============================================================================
# Frontend Setup (React Admin Panel)
# =============================================================================
print_header "Setting Up Frontend (React Admin Panel)"

if [ -d "admin" ]; then
    cd admin
    if [ -f "package.json" ]; then
        print_success "Installing npm dependencies for admin panel..."
        npm install
        print_success "Admin panel dependencies installed"
    else
        print_warning "admin/package.json not found. Skipping npm install."
    fi
    cd ..
else
    print_warning "admin directory not found. Admin panel not yet created."
fi

# =============================================================================
# Widget Setup (Modified Bill24 Widget)
# =============================================================================
print_header "Setting Up Widget"

if [ -d "widget" ]; then
    print_success "Widget directory exists"
else
    print_warning "widget directory not found. Widget files not yet set up."
fi

# =============================================================================
# Database Setup
# =============================================================================
print_header "Database Setup Instructions"

echo "To set up the database, you have two options:"
echo ""
echo "Option 1: Use Docker (recommended)"
echo "  docker-compose up -d postgres redis"
echo ""
echo "Option 2: Manual PostgreSQL and Redis"
echo "  1. Start PostgreSQL server"
echo "  2. Create database: createdb tg_ticket_agent"
echo "  3. Start Redis server"
echo ""
echo "Then run migrations:"
echo "  cd backend"
echo "  source venv/bin/activate  # or venv/Scripts/activate on Windows"
echo "  alembic upgrade head"
echo ""

# =============================================================================
# Development Server Instructions
# =============================================================================
print_header "Starting Development Servers"

echo "To start the development environment:"
echo ""
echo "1. Start database services (if using Docker):"
echo "   docker-compose -f docker-compose.dev.yml up -d postgres redis"
echo ""
echo "2. Start the backend (Terminal 1):"
echo "   cd backend"
echo "   source venv/bin/activate  # or venv/Scripts/activate on Windows"
echo "   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "3. Start the bot (Terminal 2):"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   python -m app.bot.main"
echo ""
echo "4. Start the admin panel (Terminal 3):"
echo "   cd admin"
echo "   npm run dev"
echo ""
echo "5. For the widget, serve it via nginx or a static file server"
echo ""

# =============================================================================
# Docker Development
# =============================================================================
print_header "Docker Development"

echo "To run everything with Docker:"
echo ""
echo "  docker-compose -f docker-compose.dev.yml up --build"
echo ""
echo "This will start:"
echo "  - PostgreSQL on port 5432"
echo "  - Redis on port 6379"
echo "  - Backend API on port 8000"
echo "  - Admin Panel on port 5173"
echo "  - Widget on port 8080"
echo "  - Bot (polling mode)"
echo ""

# =============================================================================
# Production Deployment
# =============================================================================
print_header "Production Deployment (Dokploy)"

echo "For production deployment on Dokploy:"
echo ""
echo "  docker-compose up --build -d"
echo ""
echo "The application will be available on PORT (default: 3000)"
echo ""
echo "Required environment variables for production:"
echo "  - TELEGRAM_BOT_TOKEN"
echo "  - DATABASE_URL"
echo "  - REDIS_URL"
echo "  - ADMIN_JWT_SECRET (use a strong random string)"
echo ""

# =============================================================================
# Summary
# =============================================================================
print_header "Setup Complete"

echo -e "${GREEN}TG-Ticket-Agent development environment is ready!${NC}"
echo ""
echo "Next steps:"
echo "  1. Update .env with your configuration"
echo "  2. Start database services"
echo "  3. Run database migrations"
echo "  4. Start development servers"
echo ""
echo "For more information, see README.md"
echo ""
