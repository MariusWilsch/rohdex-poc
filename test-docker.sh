#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}--- Testing Docker Compose Setup for Rohdex POC ---${NC}"

echo -e "${YELLOW}--- Building and starting containers ---${NC}"
docker compose up -d --build

echo -e "${YELLOW}--- Waiting for container to be healthy (20s) ---${NC}"
sleep 20

echo -e "${YELLOW}--- Container status ---${NC}"
docker compose ps

echo -e "${YELLOW}--- Testing health endpoint ---${NC}"
HEALTH_RESPONSE=$(curl -s http://localhost:8000/api/v1/health)
echo $HEALTH_RESPONSE

if [[ $HEALTH_RESPONSE == *"healthy"* ]]; then
  echo -e "${GREEN}✅ Health check passed!${NC}"
else
  echo -e "${RED}❌ Health check failed!${NC}"
  echo -e "${YELLOW}--- Checking logs for errors ---${NC}"
  docker compose logs | grep -E "ERROR|Exception|Error"
fi

echo -e "${YELLOW}--- Last 10 log lines ---${NC}"
docker compose logs --tail=10

echo -e "${YELLOW}--- Test complete ---${NC}"
echo ""
echo -e "${GREEN}The Docker setup is working correctly!${NC}"
echo -e "You can access the health check at: http://localhost:8000/api/v1/health"
echo -e "To view logs: ${YELLOW}docker compose logs -f${NC}"
echo -e "To stop the container: ${YELLOW}docker compose down${NC}" 