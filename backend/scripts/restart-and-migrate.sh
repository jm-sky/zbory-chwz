#!/bin/bash

# Script to restart Docker Compose and run database migrations
# Usage: ./restart-and-migrate.sh  (from backend/scripts/) or via repo root

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_DIR"

echo "🔄 Stopping Docker Compose services..."
docker compose down

echo ""
echo "🚀 Starting Docker Compose services..."
docker compose up -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 5

echo ""
echo "🔄 Running database migrations..."
docker compose exec app python cli.py db migrate

echo ""
echo "✅ Done! Services restarted and migrations applied."
