#!/bin/bash

# Make sure logs directory exists
mkdir -p logs

# Print a nice header
echo "==============================================" 
echo "🚀 ProtonDemand Debug Server"
echo "==============================================" 
echo "Logs will be stored in: ./logs/"
echo "Access the API at: http://localhost:8000"
echo "Press Ctrl+C to exit"
echo "==============================================" 

# Start the FastAPI server with enhanced logging
cd backend
python -m quote_system.main_api

echo "Server has stopped."