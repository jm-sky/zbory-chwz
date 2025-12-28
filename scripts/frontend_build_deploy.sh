#!/bin/bash

# Frontend Build and Deploy Script
# This script installs dependencies, builds the frontend, and deploys to /var/www/zbory-chwz
#
# Usage: scripts/frontend_build_deploy.sh

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_DIR="/var/www/zbory-chwz"

echo -e "${GREEN}🔨 Starting frontend build and deploy...${NC}"

# Step 1: Install frontend dependencies
echo -e "${YELLOW}📦 Step 1: Installing frontend dependencies...${NC}"
cd "$PROJECT_DIR"
pnpm install --frozen-lockfile

# Step 2: Build frontend
echo -e "${YELLOW}🔨 Step 2: Building frontend...${NC}"
# Clean up dist directory to avoid permission issues
rm -rf dist
# Increase Node.js memory limit to avoid "Heap Limit Reached" errors on VPS
export NODE_OPTIONS="--max-old-space-size=4096"
pnpm build
echo -e "${GREEN}✅ Frontend build completed${NC}"

# Step 3: Deploy to /var/www/zbory-chwz
echo -e "${YELLOW}📋 Step 3: Deploying to ${DEPLOY_DIR}...${NC}"

# Remove old files
sudo rm -rf "${DEPLOY_DIR:?}"/*

# Copy new build
sudo cp -r dist/* "$DEPLOY_DIR/"

# Fix ownership to caddy:deploy
sudo chown -R caddy:deploy "$DEPLOY_DIR"

echo -e "${GREEN}✅ Deployed to ${DEPLOY_DIR}${NC}"
echo -e "${GREEN}✅ Frontend build and deploy completed successfully!${NC}"

