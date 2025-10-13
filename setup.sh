#!/bin/bash

# Audio Processing Pipeline - Setup Script
# This script helps you get started quickly

set -e

echo "========================================="
echo "Audio Processing Pipeline Setup"
echo "========================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env file with your external service credentials before proceeding!"
    echo ""
    read -p "Press Enter after you've configured .env file..."
else
    echo "✓ .env file exists"
fi

echo ""
echo "Step 1: Building Docker containers..."
docker-compose build

echo ""
echo "Step 2: Starting services..."
docker-compose up -d

echo ""
echo "Step 3: Waiting for database to be ready..."
sleep 10

echo ""
echo "Step 4: Running database migrations..."
docker-compose exec -T orchestrator-api alembic upgrade head

echo ""
echo "========================================="
echo "✓ Setup Complete!"
echo "========================================="
echo ""
echo "Service URLs:"
echo "  - Frontend:     http://localhost:3000"
echo "  - API:          http://localhost:8000"
echo "  - API Docs:     http://localhost:8000/docs"
echo "  - MinIO Console: http://localhost:9001"
echo ""
echo "View logs:"
echo "  docker-compose logs -f"
echo ""
echo "Stop services:"
echo "  docker-compose down"
echo ""
echo "Happy processing! 🎵"
