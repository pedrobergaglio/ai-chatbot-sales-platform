#!/bin/bash

# Change to the app directory
cd /home/CODE/ai-chatbot-sales-platform/

# Pull latest changes from GitHub (optional - remove if you handle this separately)
#git pull

# Build and restart containers
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Show logs to verify everything is working
docker-compose logs -f
