#!/bin/bash

# Backend Restart and Migrate Script
# This script restarts the backend Docker Compose services and runs database migrations
#
# Usage: scripts/backend_restart_migrate.sh

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${GREEN}🐳 Starting backend restart and migration...${NC}"

if [ -f "$PROJECT_DIR/compose.yaml" ] || [ -f "$PROJECT_DIR/docker-compose.dev.yml" ]; then
  cd "$PROJECT_DIR"

  echo -e "${YELLOW}🔨 Building app image...${NC}"
  docker compose build app

  echo ""
  echo -e "${YELLOW}🔄 Restarting app container...${NC}"
  docker compose up -d --force-recreate app

  echo ""
  echo -e "${YELLOW}⏳ Waiting for app to be healthy...${NC}"
  sleep 5

  echo ""
  echo -e "${YELLOW}🔄 Running database migrations...${NC}"
  docker compose exec app python cli.py db migrate

  echo -e "${GREEN}✅ Backend restarted and migrations applied${NC}"
else
  echo -e "${YELLOW}⚠️  compose.yaml / docker-compose.dev.yml missing in project root, skipping backend deployment${NC}"
  exit 0
fi

echo -e "${GREEN}✅ Backend restart and migration completed successfully!${NC}"
