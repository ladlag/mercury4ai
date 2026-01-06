#!/bin/bash
# Validation script for Mercury4AI deployment

set -e

echo "========================================="
echo "Mercury4AI Deployment Validation"
echo "========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

API_KEY="${API_KEY:-your-secure-api-key-change-this}"
API_URL="${API_URL:-http://localhost:8000}"

# Function to check if service is responding
check_service() {
    local name=$1
    local url=$2
    echo -n "Checking $name... "
    if curl -s -f "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ OK${NC}"
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        return 1
    fi
}

# Function to check API endpoint
check_api() {
    local endpoint=$1
    local description=$2
    echo -n "Testing $description... "
    if curl -s -f -H "X-API-Key: $API_KEY" "$API_URL$endpoint" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ OK${NC}"
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        return 1
    fi
}

echo "1. Checking Docker Services"
echo "----------------------------"
if command -v docker-compose &> /dev/null; then
    docker-compose ps
elif command -v docker &> /dev/null; then
    docker compose ps
else
    echo -e "${RED}Docker not found${NC}"
    exit 1
fi
echo ""

echo "2. Checking Service Health"
echo "----------------------------"
check_service "PostgreSQL" "localhost:5432" || true
check_service "Redis" "localhost:6379" || true
check_service "MinIO" "http://localhost:9000/minio/health/live" || true
echo ""

echo "3. Checking API Endpoints"
echo "----------------------------"
sleep 2  # Give services time to start
check_api "/" "Root endpoint"
check_api "/api/health" "Health endpoint"
check_api "/docs" "API documentation"
echo ""

echo "4. Testing API Key Authentication"
echo "-----------------------------------"
echo -n "Testing without API key... "
if curl -s -o /dev/null -w "%{http_code}" "$API_URL/api/tasks" | grep -q "403"; then
    echo -e "${GREEN}✓ Correctly blocked${NC}"
else
    echo -e "${RED}✗ Auth not working${NC}"
fi

echo -n "Testing with API key... "
response=$(curl -s -o /dev/null -w "%{http_code}" -H "X-API-Key: $API_KEY" "$API_URL/api/tasks")
if [ "$response" = "200" ]; then
    echo -e "${GREEN}✓ Auth successful${NC}"
else
    echo -e "${RED}✗ Auth failed (HTTP $response)${NC}"
fi
echo ""

echo "5. Health Check Details"
echo "------------------------"
curl -s -H "X-API-Key: $API_KEY" "$API_URL/api/health" | python3 -m json.tool 2>/dev/null || echo "Could not get health details"
echo ""

echo "6. Testing Task Creation"
echo "-------------------------"
echo "Creating test task..."
TASK_RESPONSE=$(curl -s -X POST "$API_URL/api/tasks" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Validation Test Task",
    "description": "Automated validation test",
    "urls": ["https://example.com"],
    "crawl_config": {"verbose": true},
    "deduplication_enabled": true,
    "fallback_download_enabled": true,
    "fallback_max_size_mb": 10
  }')

TASK_ID=$(echo "$TASK_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null)

if [ -n "$TASK_ID" ]; then
    echo -e "${GREEN}✓ Task created: $TASK_ID${NC}"
    
    echo ""
    echo "7. Testing Task Run"
    echo "--------------------"
    RUN_RESPONSE=$(curl -s -X POST "$API_URL/api/tasks/$TASK_ID/run" \
      -H "X-API-Key: $API_KEY")
    
    RUN_ID=$(echo "$RUN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('run_id', ''))" 2>/dev/null)
    
    if [ -n "$RUN_ID" ]; then
        echo -e "${GREEN}✓ Run started: $RUN_ID${NC}"
        
        echo ""
        echo "8. Checking Run Status"
        echo "-----------------------"
        sleep 2
        curl -s -H "X-API-Key: $API_KEY" "$API_URL/api/runs/$RUN_ID" | python3 -m json.tool 2>/dev/null || echo "Could not get run status"
    else
        echo -e "${RED}✗ Failed to start run${NC}"
    fi
    
    echo ""
    echo "9. Cleaning Up Test Task"
    echo "-------------------------"
    curl -s -X DELETE "$API_URL/api/tasks/$TASK_ID" \
      -H "X-API-Key: $API_KEY" > /dev/null 2>&1
    echo -e "${GREEN}✓ Test task deleted${NC}"
else
    echo -e "${RED}✗ Failed to create task${NC}"
fi

echo ""
echo "========================================="
echo "Validation Complete"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Check logs: docker compose logs -f"
echo "2. Access MinIO console: http://localhost:9001"
echo "3. Access API docs: http://localhost:8000/docs"
echo ""
