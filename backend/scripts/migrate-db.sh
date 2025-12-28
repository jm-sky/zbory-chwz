#!/bin/bash

# Database Migration Script
# Migrates PostgreSQL data from one VPS server to another
#
# Usage:
#   ./migrate-db.sh <old-server> <new-server> [options]
#
# Example:
#   ./migrate-db.sh user@old-server.com user@new-server.com

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
DB_CONTAINER="zbory-chwz-db"
DB_NAME="${POSTGRES_DB:-backend}"
DB_USER="${POSTGRES_USER:-backend}"
DUMP_FILE="zbory-chwz-db-dump-$(date +%Y%m%d-%H%M%S).sql"

# Parse arguments
OLD_SERVER="${1}"
NEW_SERVER="${2}"
SKIP_DUMP="${3:-false}"

if [ -z "$OLD_SERVER" ] || [ -z "$NEW_SERVER" ]; then
  echo -e "${RED}Error: Missing required arguments${NC}"
  echo "Usage: $0 <old-server> <new-server>"
  echo "Example: $0 user@old-server.com user@new-server.com"
  exit 1
fi

echo -e "${GREEN}=== Database Migration Script ===${NC}"
echo "Old server: $OLD_SERVER"
echo "New server: $NEW_SERVER"
echo "Database: $DB_NAME"
echo "Container: $DB_CONTAINER"
echo ""

# Step 1: Create dump on old server
if [ "$SKIP_DUMP" != "true" ]; then
  echo -e "${YELLOW}Step 1: Creating database dump on old server...${NC}"
  ssh "$OLD_SERVER" "docker exec $DB_CONTAINER pg_dump -U $DB_USER -d $DB_NAME --clean --if-exists --no-owner --no-acl" > "$DUMP_FILE"
  
  if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Dump created successfully: $DUMP_FILE${NC}"
    DUMP_SIZE=$(du -h "$DUMP_FILE" | cut -f1)
    echo "  Size: $DUMP_SIZE"
  else
    echo -e "${RED}✗ Failed to create dump${NC}"
    exit 1
  fi
  echo ""
else
  echo -e "${YELLOW}Skipping dump creation (using existing file)${NC}"
  echo ""
fi

# Step 2: Copy dump to new server
echo -e "${YELLOW}Step 2: Copying dump to new server...${NC}"
scp "$DUMP_FILE" "$NEW_SERVER:/tmp/$DUMP_FILE"

if [ $? -eq 0 ]; then
  echo -e "${GREEN}✓ Dump copied successfully${NC}"
else
  echo -e "${RED}✗ Failed to copy dump${NC}"
  exit 1
fi
echo ""

# Step 3: Restore dump on new server
echo -e "${YELLOW}Step 3: Restoring database on new server...${NC}"
echo -e "${YELLOW}Warning: This will replace all existing data in the database!${NC}"
read -p "Continue? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo -e "${YELLOW}Migration cancelled${NC}"
  exit 0
fi

ssh "$NEW_SERVER" "docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME" < "$DUMP_FILE"

if [ $? -eq 0 ]; then
  echo -e "${GREEN}✓ Database restored successfully${NC}"
else
  echo -e "${RED}✗ Failed to restore database${NC}"
  exit 1
fi
echo ""

# Step 4: Cleanup
echo -e "${YELLOW}Step 4: Cleaning up...${NC}"
ssh "$NEW_SERVER" "rm /tmp/$DUMP_FILE"
echo -e "${GREEN}✓ Cleanup completed${NC}"
echo ""

echo -e "${GREEN}=== Migration completed successfully! ===${NC}"
echo ""
echo "Local dump file: $DUMP_FILE"
echo "You can delete it after verifying the migration."

