#!/bin/bash

# Start backend service
echo "Starting backend service..."
docker-compose up -d backend

# Wait for backend to initialize
echo "Waiting for backend to start..."
sleep 10

# Start frontend
echo "Starting frontend development server..."
cd frontend
pip install -r requirements.txt
streamlit run app.py