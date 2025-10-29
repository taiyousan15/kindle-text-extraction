#!/bin/bash
# Database Restore Script for Kindle OCR System

set -e

# Configuration
POSTGRES_CONTAINER="kindle_postgres_prod"
POSTGRES_USER="kindle_user"
POSTGRES_DB="kindle_ocr"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if backup file is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: Backup file not specified${NC}"
    echo "Usage: $0 <backup_file>"
    echo "Example: $0 /backups/backup_20240101_120000.sql.gz"
    exit 1
fi

BACKUP_FILE="$1"

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}Error: Backup file not found: $BACKUP_FILE${NC}"
    exit 1
fi

echo -e "${YELLOW}=== Kindle OCR Database Restore ===${NC}"
echo "Backup file: $BACKUP_FILE"
echo "Target database: $POSTGRES_DB"
echo ""
echo -e "${RED}WARNING: This will OVERWRITE the current database!${NC}"
read -p "Are you sure you want to continue? (yes/no): " -r
echo

if [[ ! $REPLY =~ ^yes$ ]]; then
    echo "Restore cancelled."
    exit 0
fi

echo -e "${YELLOW}Starting restore at $(date)${NC}"

# Drop existing connections
echo -e "${YELLOW}Dropping existing connections...${NC}"
docker exec -t "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d postgres -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$POSTGRES_DB' AND pid <> pg_backend_pid();"

# Drop and recreate database
echo -e "${YELLOW}Recreating database...${NC}"
docker exec -t "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS $POSTGRES_DB;"
docker exec -t "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE $POSTGRES_DB;"

# Restore backup
echo -e "${YELLOW}Restoring from backup...${NC}"
gunzip -c "$BACKUP_FILE" | docker exec -i "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"

echo -e "${GREEN}Restore completed successfully at $(date)${NC}"
echo -e "${YELLOW}Note: You may need to restart application services.${NC}"
