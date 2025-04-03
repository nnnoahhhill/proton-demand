#!/bin/bash

# Make sure ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "ngrok is not installed. Please install it first:"
    echo "  brew install ngrok   # on macOS"
    echo "  or download from https://ngrok.com/download"
    exit 1
fi

# Get absolute path to ngrok.yml
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
CONFIG_PATH="$SCRIPT_DIR/ngrok.yml"

# Check for ngrok.yml file
if [ ! -f "$CONFIG_PATH" ]; then
    echo "Error: ngrok.yml file not found at $CONFIG_PATH"
    exit 1
fi

# Set up variables
BACKEND_PORT=8000
FRONTEND_PORT=3001

# Start the Python backend in the background
echo "Starting Python DFM API backend on port $BACKEND_PORT..."
cd "$SCRIPT_DIR"
python dfm/manufacturing_dfm_api.py &
PYTHON_PID=$!

# Start the Next.js frontend in the background
echo "Starting Next.js frontend on port $FRONTEND_PORT..."
npm run dev &
FRONTEND_PID=$!

# Wait a moment for the servers to start
echo "Waiting for servers to start..."
sleep 5

# Start ngrok using the config file (this uses a single agent session)
echo "Starting ngrok with configuration file at $CONFIG_PATH..."
echo "Ctrl+C will stop all processes."

# Run ngrok in the foreground and capture its output
ngrok start --all --config="$CONFIG_PATH" --log=stdout | tee ngrok.log &
NGROK_PID=$!

# Give ngrok a moment to establish tunnels
sleep 5

# Extract URLs from logs - adapt pattern for current ngrok URL format
BACKEND_URL=$(grep -o "url=https://[^[:space:]]*" ngrok.log | grep -v -i "error" | head -1 | cut -d= -f2)
FRONTEND_URL=$(grep -o "url=https://[^[:space:]]*" ngrok.log | grep -v -i "error" | tail -1 | cut -d= -f2)

# Check if we got the URLs
if [ -z "$BACKEND_URL" ] || [ -z "$FRONTEND_URL" ]; then
    echo "Failed to extract ngrok URLs. Check ngrok.log for details."
    cat ngrok.log
else
    echo "====================================================="
    echo "🚀 Your application is now running with ngrok!"
    echo "====================================================="
    echo "📱 Frontend URL: $FRONTEND_URL"
    echo "⚙️  Backend URL:  $BACKEND_URL"
    echo "====================================================="
    
    # Update .env.local with backend URL
    echo "Updating .env.local with ngrok backend URL..."
    cat > .env.local << EOF
NODE_ENV=development
NEXT_PUBLIC_API_BASE_URL=$BACKEND_URL
EOF
    
    # If frontend is running, restart it to pick up the new API URL
    echo "Restarting frontend to use new API URL..."
    kill $FRONTEND_PID
    npm run dev &
    FRONTEND_PID=$!
fi

echo "Press Ctrl+C to stop all services..."

# Set up cleanup on exit
function cleanup {
    echo "Stopping all processes..."
    kill $PYTHON_PID $NGROK_PID $FRONTEND_PID 2>/dev/null
    
    # Restore original .env.local
    echo "Restoring original .env.local..."
    cat > .env.local << EOF
NODE_ENV=development
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
EOF
    
    echo "Done."
    exit 0
}

trap cleanup INT TERM

# Wait for Ctrl+C
wait 