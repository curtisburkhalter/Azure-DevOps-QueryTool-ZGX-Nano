#!/bin/bash

echo "=================================="
echo "ADO Assistant Installer"
echo "=================================="
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed."
    echo "Please install with: sudo apt-get install python3 python3-pip python3-venv"
    exit 1
fi

echo "✔ Python 3 found: $(python3 --version)"

# Create project structure
echo ""
echo "Creating project structure..."
mkdir -p ado-assistant/{backend,frontend}

# Copy files (assuming they're in current directory)
echo "Setting up backend..."
cp main.py ado-assistant/backend/
cp requirements.txt ado-assistant/backend/

echo "Setting up frontend..."
cp index.html ado-assistant/frontend/

cd ado-assistant

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install backend dependencies
echo ""
echo "Installing dependencies..."
cd backend
pip install -r requirements.txt

cd ../..

# Create start script
cat > ado-assistant/start_demo.sh << 'EOF'
#!/bin/bash

clear
echo "======================================"
echo "🤖 ADO Assistant"
echo "======================================"
echo ""

# Get IP address
IP_ADDR=$(hostname -I | awk '{print $1}')

# Kill any existing processes
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:8080 | xargs kill -9 2>/dev/null

# Start backend
echo "Starting backend server..."
cd backend
source ../venv/bin/activate
python3 main.py &
BACKEND_PID=$!
cd ..

# Start frontend server
echo "Starting frontend server..."
cd frontend
python3 -m http.server 8080 &
FRONTEND_PID=$!
cd ..

# Wait for services
echo "Waiting for services to start..."
sleep 3

echo ""
echo "======================================"
echo "✅ ADO Assistant is running!"
echo "======================================"
echo ""
echo "Access from your browser:"
echo "👉 http://localhost:8080"
echo ""
echo "Or from another device:"
echo "👉 http://${IP_ADDR}:8080"
echo ""
echo "Backend API: http://${IP_ADDR}:8000"
echo ""
echo "Configuration Required:"
echo "1. Enter your ADO Organization name"
echo "2. Enter your ADO Project name"
echo "3. Generate a Personal Access Token (PAT) from Azure DevOps"
echo "   - Go to: User Settings > Personal Access Tokens"
echo "   - Scopes needed: Work Items (Read), Code (Read), Build (Read)"
echo ""
echo "Press Ctrl+C to stop the application"
echo "======================================"

# Cleanup function
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup INT
wait
EOF

chmod +x ado-assistant/start_demo.sh

# Create README
cat > ado-assistant/README.md << 'EOF'
# ADO Assistant - AI-Powered Azure DevOps Query Tool

## Overview
ADO Assistant is a web application that allows you to query your Azure DevOps projects using natural language. It provides an intuitive interface to explore work items, pull requests, builds, and more.

## Features
- Natural language queries for Azure DevOps data
- Support for work items, bugs, user stories, pull requests, and builds
- Quick action buttons for common queries
- Real-time connection status monitoring
- Secure PAT token authentication
- Cross-platform web interface

## Setup

### Prerequisites
- Python 3.7+
- Azure DevOps account with a project
- Personal Access Token (PAT) with appropriate permissions

### Installation
1. Run the installer:
   ```bash
   ./install.sh
   ```

2. Start the application:
   ```bash
   ./start_demo.sh
   ```

### Configuration
1. Open the web interface in your browser
2. Enter your Azure DevOps organization name
3. Enter your project name
4. Enter your Personal Access Token (PAT)
5. Click "Save Configuration"

### Generating a PAT Token
1. Go to Azure DevOps
2. Click on User Settings (top right)
3. Select "Personal access tokens"
4. Click "New Token"
5. Required scopes:
   - Work Items: Read
   - Code: Read
   - Build: Read
   - (Optional) Project and Team: Read

## Usage Examples

### Natural Language Queries
- "Show me all open bugs"
- "What work items are assigned to me?"
- "Show current sprint status"
- "List recent pull requests"
- "What are the critical issues?"
- "How many bugs were closed this week?"
- "Show me high priority user stories"

### Quick Actions
Use the quick action buttons for common queries:
- 🐛 Open Bugs
- 👤 My Items
- 📊 Sprint Status
- 🔀 Pull Requests
- ⚙️ Builds
- 🚨 Critical Issues

## API Endpoints

- `GET /` - Check API status
- `POST /test-connection` - Test ADO connection
- `POST /query` - Process natural language query

## Security
- PAT tokens are stored locally in browser localStorage
- All API calls are made over HTTPS
- Tokens are never logged or stored on the server

## Troubleshooting

### Backend not connecting
- Ensure port 8000 is not in use
- Check Python dependencies are installed
- Verify firewall settings

### ADO connection fails
- Verify PAT token is valid
- Check organization and project names
- Ensure PAT has required permissions

### No results returned
- Verify project has work items
- Check query syntax
- Ensure user has access to project data

## Architecture
- Frontend: HTML5/JavaScript (vanilla)
- Backend: FastAPI (Python)
- ADO Integration: REST API v7.2
- Optional LLM: Transformers library

## License
MIT License

## Support
For issues or questions, please refer to Azure DevOps API documentation:
https://docs.microsoft.com/en-us/rest/api/azure/devops/
EOF

echo ""
echo "=================================="
echo "✅ Installation Complete!"
echo "=================================="
echo ""
echo "Project created in: ./ado-assistant/"
echo ""
echo "To start the application:"
echo "  cd ado-assistant"
echo "  ./start_demo.sh"
echo ""
echo "Then open your browser and go to:"
echo "  http://localhost:8080"
echo ""
echo "You'll need:"
echo "1. Your Azure DevOps organization name"
echo "2. Your project name"
echo "3. A Personal Access Token (PAT)"
echo ""