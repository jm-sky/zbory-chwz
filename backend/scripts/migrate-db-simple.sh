#!/bin/bash

# Simple Database Migration Script
# Non-interactive version - use with caution!
#
# Usage:
#   OLD_SERVER=user@old-server.com NEW_SERVER=user@new-server.com ./migrate-db-simple.sh

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
DB_CONTAINER="${DB_CONTAINER:-zbory-chwz-db}"
DB_NAME="${POSTGRES_DB:-backend}"
DB_USER="${POSTGRES_USER:-backend}"
DUMP_FILE="zbory-chwz-db-dump-$(date +%Y%m%d-%H%M%S).sql"

# Check required variables
if [ -z "$OLD_SERVER" ] || [ -z "$NEW_SERVER" ]; then
  echo -e "${RED}Error: OLD_SERVER and NEW_SERVER must be set${NC}"
  echo "Usage: OLD_SERVER=user@old.com NEW_SERVER=user@new.com $0"
  exit 1
fi

echo -e "${GREEN}=== Database Migration ===${NC}"
echo "Old: $OLD_SERVER"
echo "New: $NEW_SERVER"
echo ""

# Create dump
echo -e "${YELLOW}Creating dump...${NC}"
ssh "$OLD_SERVER" "docker exec $DB_CONTAINER pg_dump -U $DB_USER -d $DB_NAME --clean --if-exists --no-owner --no-acl" > "$DUMP_FILE"
echo -e "${GREEN}✓ Dump created: $DUMP_FILE${NC}"

# Copy to new server
echo -e "${YELLOW}Copying to new server...${NC}"
scp "$DUMP_FILE" "$NEW_SERVER:/tmp/$DUMP_FILE"
echo -e "${GREEN}✓ Copied${NC}"

# Restore
echo -e "${YELLOW}Restoring on new server...${NC}"
ssh "$NEW_SERVER" "docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME" < "$DUMP_FILE"
echo -e "${GREEN}✓ Restored${NC}"

# Cleanup
ssh "$NEW_SERVER" "rm /tmp/$DUMP_FILE"
echo -e "${GREEN}✓ Cleanup done${NC}"

echo ""
echo -e "${GREEN}=== Migration completed! ===${NC}"
echo "Local dump: $DUMP_FILE"

