#!/bin/bash

clear
echo "======================================"
echo "🤖 ADO Query Tool (Remote)"
echo "======================================"
echo ""

# Kill any existing processes
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:8080 | xargs kill -9 2>/dev/null

# Start backend with activated venv
echo "Starting backend server..."
cd backend
source ../ado-assistant/venv/bin/activate && python3 main.py &
BACKEND_PID=$!
cd ..

# Start frontend server
echo "Starting frontend server..."
cd frontend
python3 -m http.server 8080 &
FRONTEND_PID=$!
cd ..

# Wait for backend
echo "Waiting for services to start..."
sleep 5

# Get IP address
IP_ADDR=$(hostname -I | awk '{print $1}')

echo ""
echo "======================================"
echo "✅ ADO Assistant is running!"
echo "======================================"
echo ""
echo "Access from your browser:"
echo "👉 Local: http://localhost:8080"
echo "👉 Remote: http://${IP_ADDR}:8080"
echo ""
echo "Backend API: http://${IP_ADDR}:8000"
echo ""
echo "Configuration Required:"
echo "1. Enter your ADO Organization name"
echo "2. Enter your Project name"
echo "3. Enter your Personal Access Token (PAT)"
echo ""
echo "Press Ctrl+C to stop the application"
echo "======================================"

# Cleanup function
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "Services stopped."
    exit 0
}

trap cleanup INT
wait