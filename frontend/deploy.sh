#!/bin/bash

# Pull latest images
docker pull your-registry/patchpilot-frontend:latest
docker pull your-registry/patchpilot-backend:latest

# Stop existing services
docker-compose down

# Start new deployment
docker-compose up -d

echo "Deployment complete!"