#!/bin/bash
# Health Check Script for Kindle OCR System

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
API_URL="${API_URL:-http://localhost:8000}"
STREAMLIT_URL="${STREAMLIT_URL:-http://localhost:8501}"

echo -e "${GREEN}=== Kindle OCR Health Check ===${NC}"
echo ""

# Function to check service
check_service() {
    local name=$1
    local url=$2
    local timeout=${3:-5}

    echo -n "Checking $name... "

    if curl -sf --max-time "$timeout" "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ OK${NC}"
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        return 1
    fi
}

# Check services
FAILED=0

check_service "API Health" "$API_URL/health" 5 || FAILED=$((FAILED + 1))
check_service "API Docs" "$API_URL/docs" 5 || FAILED=$((FAILED + 1))
check_service "Streamlit" "$STREAMLIT_URL/_stcore/health" 5 || FAILED=$((FAILED + 1))

# Check Docker containers
echo ""
echo "Docker Container Status:"
docker-compose -f docker-compose.prod.yml ps

# Summary
echo ""
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All services are healthy!${NC}"
    exit 0
else
    echo -e "${RED}$FAILED service(s) failed health check!${NC}"
    exit 1
fi
