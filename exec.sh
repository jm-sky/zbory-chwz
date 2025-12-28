#!/bin/bash

# Docker Compose Exec Wrapper
# This script executes commands in the Docker Compose container
#
# Usage: ./exec.sh [command] [arguments...]
# Example: ./exec.sh                    # Runs: python -m cli (interactive menu)
# Example: ./exec.sh python -m cli users list
# Example: ./exec.sh python -m cli db migrate

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"

# Function to detect docker-compose file from running containers
detect_compose_file() {
  local compose_file=""
  
  # Check for production container (backend)
  if docker ps --format '{{.Names}}' | grep -q "^backend$"; then
    # Try to get compose file from container labels
    local config_files=$(docker inspect backend --format '{{index .Config.Labels "com.docker.compose.project.config_files"}}' 2>/dev/null || echo "")
    if [ -n "$config_files" ]; then
      # Extract filename from full path
      compose_file=$(basename "$config_files" | head -n1)
    else
      # Fallback: assume docker-compose.yml for production container
      compose_file="docker-compose.yml"
    fi
  # Check for development container (zbory-chwz-app)
  elif docker ps --format '{{.Names}}' | grep -q "^zbory-chwz-app$"; then
    # Try to get compose file from container labels
    local config_files=$(docker inspect zbory-chwz-app --format '{{index .Config.Labels "com.docker.compose.project.config_files"}}' 2>/dev/null || echo "")
    if [ -n "$config_files" ]; then
      # Extract filename from full path
      compose_file=$(basename "$config_files" | head -n1)
    else
      # Fallback: assume docker-compose.dev.yml for development container
      compose_file="docker-compose.dev.yml"
    fi
  fi
  
  # If still not found, try to find any app container and check its labels
  if [ -z "$compose_file" ]; then
    local app_container=$(docker ps --format '{{.Names}}' | grep -E "(backend|zbory-chwz-app)" | head -n1)
    if [ -n "$app_container" ]; then
      local config_files=$(docker inspect "$app_container" --format '{{index .Config.Labels "com.docker.compose.project.config_files"}}' 2>/dev/null || echo "")
      if [ -n "$config_files" ]; then
        compose_file=$(basename "$config_files" | head -n1)
      fi
    fi
  fi
  
  # Final fallback: check which files exist
  if [ -z "$compose_file" ]; then
    if [ -f "$BACKEND_DIR/docker-compose.yml" ]; then
      compose_file="docker-compose.yml"
    elif [ -f "$BACKEND_DIR/docker-compose.dev.yml" ]; then
      compose_file="docker-compose.dev.yml"
    fi
  fi
  
  echo "$compose_file"
}

# Determine which docker-compose file to use
COMPOSE_FILE=$(detect_compose_file)

if [ -z "$COMPOSE_FILE" ]; then
  echo -e "${RED}Error: Could not detect docker-compose file${NC}"
  echo -e "${YELLOW}Make sure at least one container is running or docker-compose file exists in $BACKEND_DIR${NC}"
  exit 1
fi

# Check if backend directory exists
if [ ! -d "$BACKEND_DIR" ]; then
  echo -e "${RED}Error: Backend directory not found: $BACKEND_DIR${NC}"
  exit 1
fi

# Check if docker-compose file exists
if [ ! -f "$BACKEND_DIR/$COMPOSE_FILE" ]; then
  echo -e "${RED}Error: Docker Compose file not found: $BACKEND_DIR/$COMPOSE_FILE${NC}"
  exit 1
fi

cd "$BACKEND_DIR"

# Determine container name based on compose file
if [ "$COMPOSE_FILE" = "docker-compose.yml" ]; then
  CONTAINER_NAME="backend"
elif [ "$COMPOSE_FILE" = "docker-compose.dev.yml" ]; then
  CONTAINER_NAME="zbory-chwz-app"
else
  # Try to get container name from compose file
  CONTAINER_NAME=$(docker compose -f "$COMPOSE_FILE" ps app --format json 2>/dev/null | grep -o '"Name":"[^"]*"' | head -n1 | cut -d'"' -f4 || echo "app")
fi

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
  echo -e "${YELLOW}Warning: Container '${CONTAINER_NAME}' is not running. Starting it...${NC}"
  docker compose -f "$COMPOSE_FILE" up -d app
  
  # Wait a bit for container to be ready
  echo -e "${YELLOW}Waiting for container to be ready...${NC}"
  sleep 3
fi

# If no arguments provided, default to 'python -m cli'
if [ $# -eq 0 ]; then
  CMD_ARGS=("python" "-m" "cli")
else
  CMD_ARGS=("python" "-m" "cli" "$@")
fi

# Execute command in container
echo -e "${GREEN}Executing in container (${COMPOSE_FILE}):${NC} ${CMD_ARGS[*]}"
docker compose -f "$COMPOSE_FILE" exec app "${CMD_ARGS[@]}"

