#!/bin/bash

# Deploy script for gama-software.com
# This script should be placed on the server at /var/www/gama-software/deploy.sh

set -e  # Exit on error

echo "🚀 Starting deployment..."

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Change to project directory
cd /var/www/gama-software

echo -e "${YELLOW}📥 Pulling latest changes from Git...${NC}"
git pull origin main

echo -e "${YELLOW}🛑 Stopping containers...${NC}"
docker-compose -f build/docker-compose.yml down

echo -e "${YELLOW}🔨 Building Docker images...${NC}"
docker-compose -f build/docker-compose.yml build --no-cache

echo -e "${YELLOW}🚀 Starting containers...${NC}"
docker-compose -f build/docker-compose.yml up -d

echo -e "${YELLOW}🧹 Cleaning up unused Docker resources...${NC}"
docker system prune -f

echo -e "${YELLOW}📊 Checking container status...${NC}"
docker-compose -f build/docker-compose.yml ps

echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo -e "${GREEN}🌐 Site should be live at https://gama-software.com${NC}"
