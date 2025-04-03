#!/bin/bash

# Start the Python backend in the background
echo "Starting Python DFM API backend..."
cd $(dirname $0)
python dfm/manufacturing_dfm_api.py &
PYTHON_PID=$!

# Start the Next.js frontend
echo "Starting Next.js frontend..."
npm run dev

# When the frontend is stopped, also stop the Python backend
echo "Stopping Python backend (PID: $PYTHON_PID)..."
kill $PYTHON_PID 