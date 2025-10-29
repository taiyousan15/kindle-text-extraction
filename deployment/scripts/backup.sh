#!/bin/bash
# Database Backup Script for Kindle OCR System

set -e

# Configuration
BACKUP_DIR="/backups"
RETENTION_DAYS=30
POSTGRES_CONTAINER="kindle_postgres_prod"
POSTGRES_USER="kindle_user"
POSTGRES_DB="kindle_ocr"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_$DATE.sql.gz"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== Kindle OCR Database Backup ===${NC}"
echo "Starting backup at $(date)"

# Create backup directory if not exists
mkdir -p "$BACKUP_DIR"

# Perform backup
echo -e "${YELLOW}Creating backup...${NC}"
docker exec -t "$POSTGRES_CONTAINER" pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$BACKUP_FILE"

# Check if backup was successful
if [ -f "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo -e "${GREEN}Backup created successfully: $BACKUP_FILE (${BACKUP_SIZE})${NC}"
else
    echo -e "${RED}Backup failed!${NC}"
    exit 1
fi

# Clean up old backups
echo -e "${YELLOW}Cleaning up old backups (older than ${RETENTION_DAYS} days)...${NC}"
find "$BACKUP_DIR" -name "backup_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete
REMAINING_BACKUPS=$(ls -1 "$BACKUP_DIR"/backup_*.sql.gz 2>/dev/null | wc -l)
echo -e "${GREEN}Cleanup complete. ${REMAINING_BACKUPS} backups remaining.${NC}"

echo "Backup completed at $(date)"
