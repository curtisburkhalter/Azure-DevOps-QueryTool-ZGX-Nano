# ADO Assistant
### This demo was created during my time as an AI Product Manager at HP

A natural language query tool for Azure DevOps that allows sales and marketing teams to explore work items, pull requests, builds, and more using conversational queries. Built to demonstrate local AI capabilities on the HP ZGX Nano AI Station.

## Overview

ADO Assistant provides an intuitive web interface for querying Azure DevOps projects without requiring knowledge of WIQL (Work Item Query Language) or the Azure DevOps API. Users can ask questions in plain English and receive formatted results instantly.

The application consists of a FastAPI backend that handles natural language processing and Azure DevOps API integration, paired with a responsive HTML frontend for user interaction.

## Features

- Natural language queries for Azure DevOps data
- Support for work items, bugs, user stories, pull requests, and builds
- Quick action buttons for common queries
- Real-time connection status monitoring
- Secure PAT token authentication (stored locally in browser)
- Optional LLM integration using Microsoft Phi-3-mini for enhanced query processing
- Cross-platform web interface accessible from any device on the network

## System Requirements

- Python 3.7 or higher
- Network access to Azure DevOps (visualstudio.com domain)
- Azure DevOps account with an active project
- Personal Access Token (PAT) with appropriate permissions

**Optional for LLM Support:**
- Additional 8GB+ RAM for model loading
- PyTorch and Transformers libraries

## Installation

### Quick Install

1. Place all files in the same directory
2. Run the installer script:

```bash
chmod +x installer.sh
./installer.sh
```

The installer creates the following project structure:

```
ado-assistant/
├── backend/
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   └── index.html
├── venv/
├── start_demo.sh
└── README.md
```

### Manual Installation

If you prefer manual setup:

```bash
# Create project directories
mkdir -p ado-assistant/backend ado-assistant/frontend

# Copy files to appropriate locations
cp main.py ado-assistant/backend/
cp requirements.txt ado-assistant/backend/
cp index.html ado-assistant/frontend/

# Create and activate virtual environment
cd ado-assistant
python3 -m venv venv
source venv/bin/activate

# Install dependencies
cd backend
pip install -r requirements.txt
```

## Starting the Demo

### Standard Start

```bash
cd ado-assistant
./start_demo.sh
```

### Remote Access Start

For accessing the demo from other devices on the network:

```bash
./start_demo_remote.sh
```

The application will display:
- Local access URL: http://localhost:8080
- Network access URL: http://[YOUR_IP]:8080
- Backend API: http://[YOUR_IP]:8000

## Configuration

**IMPORTANT:** Sales teams must configure the following settings in the web interface before use.

### Required Configuration

1. **Organization Name** - Your Azure DevOps organization (the subdomain in your ADO URL)
   - Example: If your URL is `https://contoso.visualstudio.com`, enter `contoso`

2. **Project Name** - The name of your Azure DevOps project
   - This must match exactly as it appears in Azure DevOps

3. **Personal Access Token (PAT)** - Authentication token for API access

### Generating a PAT Token

1. Navigate to Azure DevOps and sign in
2. Click your profile icon (top right) and select **User Settings**
3. Select **Personal access tokens**
4. Click **New Token**
5. Configure the token with these minimum scopes:
   - Work Items: **Read**
   - Code: **Read**
   - Build: **Read**
   - (Optional) Project and Team: **Read**
6. Copy the generated token immediately (it will not be shown again)

## Usage Examples

### Natural Language Queries

Enter questions in the text area and press Enter or click the query button:

- "Show me all open bugs"
- "What work items are assigned to me?"
- "Show current sprint status"
- "List recent pull requests"
- "What are the critical issues?"
- "How many bugs were closed this week?"
- "Show me high priority user stories"
- "What's the status of our builds?"

### Quick Action Buttons

The interface provides six quick action buttons for common queries:

| Button | Query Executed |
|--------|----------------|
| Open Bugs | "Show me all open bugs" |
| My Items | "What's assigned to me?" |
| Sprint Status | "What's the current sprint status?" |
| Pull Requests | "Show recent pull requests" |
| Builds | "Show recent builds" |
| Critical Issues | "What are the critical issues?" |

## Architecture

### Backend (FastAPI)

The backend (`main.py`) provides three API endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check and status |
| `/test-connection` | POST | Validate ADO credentials |
| `/query` | POST | Process natural language queries |

The `QueryProcessor` class handles natural language interpretation and converts queries to appropriate Azure DevOps WIQL queries or API calls.

### Frontend (HTML/JavaScript)

The frontend provides:
- Configuration form with local storage persistence
- Real-time backend connection monitoring
- Query input with quick action buttons
- Formatted response display with metadata
- Query statistics tracking

### Azure DevOps Integration

The application connects to Azure DevOps using the REST API v7.2-preview. Supported operations include:
- Work item queries via WIQL
- Pull request retrieval
- Build status queries
- Project and team information

## Troubleshooting

### Backend Not Starting

- Verify Python 3.7+ is installed: `python3 --version`
- Check if port 8000 is already in use: `lsof -i :8000`
- Ensure all dependencies installed: `pip install -r requirements.txt`

### Frontend Not Loading

- Check if port 8080 is already in use: `lsof -i :8080`
- Verify the frontend server started successfully
- Try accessing via localhost first before network IP

### ADO Connection Fails

- Verify the organization name matches your ADO subdomain exactly
- Confirm the project name is spelled correctly (case-sensitive)
- Check that your PAT token has not expired
- Ensure the PAT has the required permission scopes

### No Results Returned

- Verify your project contains work items
- Check that your user account has access to the project data
- Try a simpler query like "show all work items" to test connectivity

### LLM Model Not Loading

The LLM component (Microsoft Phi-3-mini) is optional. If it fails to load:
- The application continues to function using rule-based query processing
- Check available system memory (requires 8GB+ free RAM)
- To disable LLM, comment out the transformers and torch lines in `requirements.txt`

## Dependencies

**Core Requirements:**
- fastapi >= 0.100.0
- uvicorn[standard] >= 0.24.0
- requests >= 2.31.0
- python-multipart >= 0.0.6
- pydantic >= 2.0.0

**Optional LLM Support:**
- transformers >= 4.35.0
- torch >= 2.2.0

## Security Notes

- PAT tokens are stored in the browser's localStorage (client-side only)
- Tokens are never logged or stored on the backend server
- All Azure DevOps API calls use HTTPS
- The backend runs on localhost by default; network exposure is optional

## Support

If you have questions about this demo contact Curtis Burkhalter at curtisburkhalter@gmail.com
