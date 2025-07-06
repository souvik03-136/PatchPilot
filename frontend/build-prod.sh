#!/bin/bash

# Build frontend image
echo "Building frontend Docker image..."
docker build -t patchpilot-frontend:latest ./frontend

# Build backend image (if needed)
# docker build -t patchpilot-backend:latest ./backend

echo "Build complete!"