#!/bin/bash

# Make sure ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "ngrok is not installed. Please install it first:"
    echo "  brew install ngrok   # on macOS"
    echo "  or download from https://ngrok.com/download"
    exit 1
fi

# Check authentication
if ! ngrok config check &> /dev/null; then
    echo "ngrok is not authenticated. Please run:"
    echo "  ngrok config add-authtoken YOUR_AUTH_TOKEN"
    echo "Get your auth token from https://dashboard.ngrok.com/get-started/your-authtoken"
    exit 1
fi

# Start ngrok with config file if it exists
if [ -f "ngrok.yml" ]; then
    echo "Starting ngrok with config file..."
    ngrok start --config=ngrok.yml --all
else
    # Otherwise, start both tunnels directly
    echo "No ngrok.yml config found. Starting tunnels directly..."
    echo "Starting backend tunnel (port 8000)..."
    ngrok http 8000 &
    NGROK_BACKEND_PID=$!
    
    echo "Waiting for backend tunnel to establish..."
    sleep 3
    
    echo "Starting frontend tunnel (port 3001)..."
    ngrok http 3001 &
    NGROK_FRONTEND_PID=$!
    
    echo "ngrok tunnels are running."
    echo "Press Ctrl+C to stop the tunnels."
    
    # Wait for Ctrl+C
    trap "kill $NGROK_BACKEND_PID $NGROK_FRONTEND_PID; exit 0" INT
    wait
fi 