#!/bin/bash

# Set up variables
BACKEND_PORT=8000
FRONTEND_PORT=3001

# Start the Python backend in the background
echo "Starting Python DFM API backend on port $BACKEND_PORT..."
cd $(dirname $0)
python dfm/manufacturing_dfm_api.py &
PYTHON_PID=$!

# Start ngrok for the backend in the background
echo "Starting ngrok tunnel for backend (port $BACKEND_PORT)..."
ngrok http $BACKEND_PORT --log=stdout > ngrok-backend.log &
NGROK_BACKEND_PID=$!

# Wait for ngrok to start and get the public URL
echo "Waiting for ngrok tunnel to be established..."
sleep 5

# Get the ngrok URL from the log file
NGROK_BACKEND_URL=$(grep -o 'url=https://[^ ]*' ngrok-backend.log | head -1 | cut -d= -f2)

if [ -z "$NGROK_BACKEND_URL" ]; then
  echo "Failed to get ngrok URL. Check ngrok-backend.log for details."
  echo "Killing background processes..."
  kill $PYTHON_PID $NGROK_BACKEND_PID
  exit 1
fi

echo "Backend accessible at: $NGROK_BACKEND_URL"

# Create/update .env.local with the ngrok URL
echo "Updating .env.local with ngrok URL..."
cat > .env.local << EOF
NODE_ENV=development
NEXT_PUBLIC_API_BASE_URL=$NGROK_BACKEND_URL
EOF

# Start the Next.js frontend
echo "Starting Next.js frontend..."
echo "NOTE: The frontend will be available at http://localhost:$FRONTEND_PORT"
echo "You can expose the frontend with: ngrok http $FRONTEND_PORT (in another terminal)"

npm run dev

# When the frontend is stopped, also stop the Python backend and ngrok
echo "Stopping background processes..."
kill $PYTHON_PID $NGROK_BACKEND_PID

# Restore original .env.local
echo "Restoring original .env.local..."
cat > .env.local << EOF
NODE_ENV=development
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
EOF

echo "Done." 