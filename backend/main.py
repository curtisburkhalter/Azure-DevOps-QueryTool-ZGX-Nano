from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import uvicorn
import requests
from requests.auth import HTTPBasicAuth
import json
import os
from typing import Optional, Dict, Any, List
import base64
from urllib.parse import quote

app = FastAPI()

# Enable CORS for local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Try to load LLM for natural language processing
model_loaded = False
llm_pipeline = None

try:
    from transformers import pipeline
    print("Loading LLM model for query processing...")
    
    # You can use a different model if preferred
    llm_pipeline = pipeline(
        "text-generation",
        model="microsoft/Phi-3-mini-4k-instruct",
        device="cpu",
        trust_remote_code=True
    )
    model_loaded = True
    print("Model loaded successfully!")
    
except Exception as e:
    print(f"Could not load LLM model: {e}")
    print("Running without AI assistance - will use direct ADO API queries")

class ADOConfig(BaseModel):
    organization: str
    project: str
    pat: str

class QueryRequest(BaseModel):
    query: str
    config: ADOConfig

class ADOClient:
    """Azure DevOps API Client"""
    
    def __init__(self, organization: str, project: str, pat: str):
        self.organization = organization
        self.project = project
        self.pat = pat
        # Updated for visualstudio.com domain
        self.base_url = f"https://{organization}.visualstudio.com"
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Basic ' + base64.b64encode(f":{pat}".encode()).decode()
        }
    
    def test_connection(self) -> Dict:
        """Test ADO connection by fetching projects"""
        try:
            url = f"{self.base_url}/_apis/projects?api-version=7.2-preview"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "connected": True,
                    "project_count": data.get("count", 0),
                    "projects": [p["name"] for p in data.get("value", [])]
                }
            else:
                return {
                    "connected": False, 
                    "error": f"Status {response.status_code}: {response.text[:200]}"
                }
                
        except Exception as e:
            return {"connected": False, "error": str(e)}
    
    def get_work_items(self, wiql: str) -> Dict:
        """Execute WIQL query to get work items"""
        # URL encode the project name for the API endpoint
        encoded_project = quote(self.project)
        url = f"{self.base_url}/{encoded_project}/_apis/wit/wiql?api-version=7.2-preview"
        
        body = {
            "query": wiql
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=body, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                # More detailed error for debugging
                error_detail = response.text[:500] if response.text else f"Status {response.status_code}"
                return {"error": f"Query failed: {response.status_code} - {error_detail}"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def get_work_item_details(self, ids: List[int]) -> List[Dict]:
        """Get detailed information for work items"""
        if not ids:
            return []
            
        # ADO API allows max 200 IDs per request
        ids = ids[:200]
        ids_str = ",".join(map(str, ids))
        
        encoded_project = quote(self.project)
        url = f"{self.base_url}/{encoded_project}/_apis/wit/workitems?ids={ids_str}&$expand=all&api-version=7.2-preview"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                return response.json().get("value", [])
            else:
                print(f"Error fetching work item details: Status {response.status_code}")
                return []
                
        except Exception as e:
            print(f"Error fetching work item details: {e}")
            return []
    
    def get_pull_requests(self, status: str = "active") -> List[Dict]:
        """Get pull requests"""
        encoded_project = quote(self.project)
        url = f"{self.base_url}/{encoded_project}/_apis/git/pullrequests?searchCriteria.status={status}&api-version=7.2-preview"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                return response.json().get("value", [])
            else:
                print(f"Error fetching pull requests: Status {response.status_code}")
                return []
                
        except Exception as e:
            print(f"Error fetching pull requests: {e}")
            return []
    
    def get_builds(self, top: int = 10) -> List[Dict]:
        """Get recent builds"""
        encoded_project = quote(self.project)
        url = f"{self.base_url}/{encoded_project}/_apis/build/builds?$top={top}&api-version=7.2-preview"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                return response.json().get("value", [])
            else:
                print(f"Error fetching builds: Status {response.status_code}")
                return []
                
        except Exception as e:
            print(f"Error fetching builds: {e}")
            return []

class QueryProcessor:
    """Process natural language queries into ADO API calls"""
    
    def __init__(self, ado_client: ADOClient):
        self.client = ado_client
        
    def process_query(self, query: str) -> Dict:
        """Convert natural language query to ADO API calls and format response"""
        
        query_lower = query.lower()
        
        # Detect query type and execute appropriate API calls
        
        if "bug" in query_lower:
            return self._query_bugs(query_lower)
        
        elif "assigned to me" in query_lower or "my items" in query_lower or "my work" in query_lower:
            return self._query_my_items()
        
        elif "sprint" in query_lower:
            return self._query_sprint_status()
        
        elif "pull request" in query_lower or " pr " in query_lower:
            return self._query_pull_requests()
        
        elif "build" in query_lower or "pipeline" in query_lower:
            return self._query_builds()
        
        elif "critical" in query_lower or "high priority" in query_lower:
            return self._query_critical_items()
        
        elif "user stor" in query_lower:
            return self._query_user_stories(query_lower)
        
        elif "closed" in query_lower or "completed" in query_lower:
            return self._query_completed_items(query_lower)
        
        else:
            # Generic work item query
            return self._query_all_work_items()
    
    def _query_bugs(self, query: str) -> Dict:
        """Query for bugs"""
        
        if "open" in query or "active" in query:
            wiql = f"""
            SELECT [System.Id], [System.Title], [System.State], [System.AssignedTo], [Microsoft.VSTS.Common.Priority]
            FROM WorkItems
            WHERE [System.TeamProject] = '{self.client.project}'
            AND [System.WorkItemType] = 'Bug'
            AND [System.State] NOT IN ('Closed', 'Resolved', 'Done')
            ORDER BY [Microsoft.VSTS.Common.Priority] ASC
            """
        else:
            wiql = f"""
            SELECT [System.Id], [System.Title], [System.State], [System.AssignedTo], [Microsoft.VSTS.Common.Priority]
            FROM WorkItems
            WHERE [System.TeamProject] = '{self.client.project}'
            AND [System.WorkItemType] = 'Bug'
            ORDER BY [System.ChangedDate] DESC
            """
        
        result = self.client.get_work_items(wiql)
        
        if "error" in result:
            return {
                "answer": f"Failed to query bugs: {result['error']}",
                "query_type": "bugs",
                "items_found": 0,
                "api_calls": 1
            }
        
        work_items = result.get("workItems", [])
        
        if work_items:
            # Get details for the work items
            ids = [wi["id"] for wi in work_items[:20]]  # Limit to 20 items
            details = self.client.get_work_item_details(ids)
            
            # Format response
            answer = f"Found {len(work_items)} bug(s):\n\n"
            
            for item in details[:10]:  # Show top 10
                fields = item.get("fields", {})
                answer += f"• #{item['id']}: {fields.get('System.Title', 'No title')}\n"
                answer += f"  State: {fields.get('System.State', 'Unknown')}"
                answer += f" | Priority: {fields.get('Microsoft.VSTS.Common.Priority', 'Not set')}"
                assignee = fields.get('System.AssignedTo', {})
                if isinstance(assignee, dict):
                    answer += f" | Assigned to: {assignee.get('displayName', 'Unassigned')}\n\n"
                else:
                    answer += f" | Assigned to: Unassigned\n\n"
            
            if len(work_items) > 10:
                answer += f"... and {len(work_items) - 10} more bugs"
            
            return {
                "answer": answer,
                "query_type": "bugs",
                "items_found": len(work_items),
                "api_calls": 2
            }
        else:
            return {
                "answer": "No bugs found matching your criteria.",
                "query_type": "bugs",
                "items_found": 0,
                "api_calls": 1
            }
    
    def _query_my_items(self) -> Dict:
        """Query for items assigned to current user"""
        wiql = f"""
        SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State]
        FROM WorkItems
        WHERE [System.TeamProject] = '{self.client.project}'
        AND [System.AssignedTo] = @Me
        AND [System.State] NOT IN ('Closed', 'Done', 'Removed')
        ORDER BY [Microsoft.VSTS.Common.Priority] ASC, [System.ChangedDate] DESC
        """
        
        result = self.client.get_work_items(wiql)
        
        if "error" in result:
            return {
                "answer": f"Failed to query your items: {result['error']}",
                "query_type": "my_items",
                "items_found": 0,
                "api_calls": 1
            }
        
        work_items = result.get("workItems", [])
        
        if work_items:
            ids = [wi["id"] for wi in work_items[:20]]
            details = self.client.get_work_item_details(ids)
            
            answer = f"You have {len(work_items)} work item(s) assigned:\n\n"
            
            # Group by type
            by_type = {}
            for item in details:
                fields = item.get("fields", {})
                wi_type = fields.get("System.WorkItemType", "Unknown")
                if wi_type not in by_type:
                    by_type[wi_type] = []
                by_type[wi_type].append(item)
            
            for wi_type, items in by_type.items():
                answer += f"{wi_type}s ({len(items)}):\n"
                for item in items[:5]:
                    fields = item.get("fields", {})
                    answer += f"• #{item['id']}: {fields.get('System.Title', 'No title')} [{fields.get('System.State', 'Unknown')}]\n"
                answer += "\n"
            
            return {
                "answer": answer,
                "query_type": "my_items",
                "items_found": len(work_items),
                "api_calls": 2
            }
        else:
            return {
                "answer": "You have no work items currently assigned to you.",
                "query_type": "my_items",
                "items_found": 0,
                "api_calls": 1
            }
    
    def _query_sprint_status(self) -> Dict:
        """Query current sprint status"""
        wiql = f"""
        SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State], [System.AssignedTo]
        FROM WorkItems
        WHERE [System.TeamProject] = '{self.client.project}'
        AND [System.IterationPath] UNDER '{self.client.project}'
        AND [System.State] NOT IN ('Removed')
        ORDER BY [System.WorkItemType], [System.State]
        """
        
        result = self.client.get_work_items(wiql)
        
        if "error" in result:
            return {
                "answer": f"Failed to query sprint status: {result['error']}",
                "query_type": "sprint",
                "items_found": 0,
                "api_calls": 1
            }
        
        work_items = result.get("workItems", [])
        
        if work_items:
            ids = [wi["id"] for wi in work_items[:50]]
            details = self.client.get_work_item_details(ids)
            
            # Calculate statistics
            stats = {
                "total": len(work_items),
                "by_state": {},
                "by_type": {}
            }
            
            for item in details:
                fields = item.get("fields", {})
                state = fields.get("System.State", "Unknown")
                wi_type = fields.get("System.WorkItemType", "Unknown")
                
                stats["by_state"][state] = stats["by_state"].get(state, 0) + 1
                stats["by_type"][wi_type] = stats["by_type"].get(wi_type, 0) + 1
            
            answer = f"Current Sprint Status:\n\n"
            answer += f"Total Work Items: {stats['total']}\n\n"
            
            answer += "By State:\n"
            for state, count in sorted(stats["by_state"].items()):
                answer += f"• {state}: {count}\n"
            
            answer += "\nBy Type:\n"
            for wi_type, count in sorted(stats["by_type"].items()):
                answer += f"• {wi_type}: {count}\n"
            
            # Calculate completion percentage
            completed = stats["by_state"].get("Done", 0) + stats["by_state"].get("Closed", 0)
            if stats["total"] > 0:
                completion = (completed / stats["total"]) * 100
                answer += f"\nCompletion: {completion:.1f}% ({completed}/{stats['total']})"
            
            return {
                "answer": answer,
                "query_type": "sprint",
                "items_found": len(work_items),
                "api_calls": 2
            }
        else:
            return {
                "answer": "No work items found in the current sprint.",
                "query_type": "sprint",
                "items_found": 0,
                "api_calls": 1
            }
    
    def _query_pull_requests(self) -> Dict:
        """Query pull requests"""
        prs = self.client.get_pull_requests("active")
        
        if prs:
            answer = f"Found {len(prs)} active pull request(s):\n\n"
            
            for pr in prs[:10]:
                answer += f"• PR #{pr['pullRequestId']}: {pr['title']}\n"
                answer += f"  By: {pr['createdBy']['displayName']}"
                answer += f" | Target: {pr['targetRefName'].replace('refs/heads/', '')}\n"
                answer += f"  Status: {pr['status']} | Reviewers: {len(pr.get('reviewers', []))}\n\n"
            
            if len(prs) > 10:
                answer += f"... and {len(prs) - 10} more pull requests"
            
            return {
                "answer": answer,
                "query_type": "pull_requests",
                "items_found": len(prs),
                "api_calls": 1
            }
        else:
            return {
                "answer": "No active pull requests found.",
                "query_type": "pull_requests",
                "items_found": 0,
                "api_calls": 1
            }
    
    def _query_builds(self) -> Dict:
        """Query recent builds"""
        builds = self.client.get_builds(10)
        
        if builds:
            answer = f"Recent builds:\n\n"
            
            success_count = 0
            failed_count = 0
            
            for build in builds:
                status = build.get("status", "unknown")
                result = build.get("result", "in progress")
                
                if result == "succeeded":
                    success_count += 1
                    emoji = "✅"
                elif result == "failed":
                    failed_count += 1
                    emoji = "❌"
                else:
                    emoji = "⏳"
                
                answer += f"{emoji} Build #{build['id']}: {build.get('definition', {}).get('name', 'Unknown')}\n"
                answer += f"   Status: {result} | Requested by: {build.get('requestedFor', {}).get('displayName', 'Unknown')}\n"
                answer += f"   Started: {build.get('startTime', 'N/A')}\n\n"
            
            answer += f"\nSummary: {success_count} succeeded, {failed_count} failed"
            
            return {
                "answer": answer,
                "query_type": "builds",
                "items_found": len(builds),
                "api_calls": 1
            }
        else:
            return {
                "answer": "No recent builds found.",
                "query_type": "builds",
                "items_found": 0,
                "api_calls": 1
            }
    
    def _query_critical_items(self) -> Dict:
        """Query critical/high priority items"""
        wiql = f"""
        SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State], [Microsoft.VSTS.Common.Priority]
        FROM WorkItems
        WHERE [System.TeamProject] = '{self.client.project}'
        AND [Microsoft.VSTS.Common.Priority] <= 2
        AND [System.State] NOT IN ('Closed', 'Done', 'Resolved')
        ORDER BY [Microsoft.VSTS.Common.Priority] ASC, [System.ChangedDate] DESC
        """
        
        result = self.client.get_work_items(wiql)
        
        if "error" in result:
            return {
                "answer": f"Failed to query critical items: {result['error']}",
                "query_type": "critical",
                "items_found": 0,
                "api_calls": 1
            }
        
        work_items = result.get("workItems", [])
        
        if work_items:
            ids = [wi["id"] for wi in work_items[:20]]
            details = self.client.get_work_item_details(ids)
            
            answer = f"Found {len(work_items)} critical/high priority item(s):\n\n"
            
            for item in details[:10]:
                fields = item.get("fields", {})
                priority = fields.get('Microsoft.VSTS.Common.Priority', 'Not set')
                priority_label = "🔴 Critical" if priority == 1 else "🟠 High"
                
                answer += f"{priority_label} #{item['id']}: {fields.get('System.Title', 'No title')}\n"
                answer += f"  Type: {fields.get('System.WorkItemType', 'Unknown')}"
                answer += f" | State: {fields.get('System.State', 'Unknown')}"
                assignee = fields.get('System.AssignedTo', {})
                if isinstance(assignee, dict):
                    answer += f" | Assigned: {assignee.get('displayName', 'Unassigned')}\n\n"
                else:
                    answer += f" | Assigned: Unassigned\n\n"
            
            return {
                "answer": answer,
                "query_type": "critical",
                "items_found": len(work_items),
                "api_calls": 2
            }
        else:
            return {
                "answer": "No critical or high priority items found.",
                "query_type": "critical",
                "items_found": 0,
                "api_calls": 1
            }
    
    def _query_user_stories(self, query: str) -> Dict:
        """Query user stories"""
        
        if "high priority" in query:
            wiql = f"""
            SELECT [System.Id], [System.Title], [System.State], [Microsoft.VSTS.Common.Priority]
            FROM WorkItems
            WHERE [System.TeamProject] = '{self.client.project}'
            AND [System.WorkItemType] = 'User Story'
            AND [Microsoft.VSTS.Common.Priority] <= 2
            ORDER BY [Microsoft.VSTS.Common.Priority] ASC
            """
        else:
            wiql = f"""
            SELECT [System.Id], [System.Title], [System.State], [System.AssignedTo]
            FROM WorkItems
            WHERE [System.TeamProject] = '{self.client.project}'
            AND [System.WorkItemType] = 'User Story'
            AND [System.State] NOT IN ('Closed', 'Done', 'Removed')
            ORDER BY [System.ChangedDate] DESC
            """
        
        result = self.client.get_work_items(wiql)
        
        if "error" in result:
            return {
                "answer": f"Failed to query user stories: {result['error']}",
                "query_type": "user_stories",
                "items_found": 0,
                "api_calls": 1
            }
        
        work_items = result.get("workItems", [])
        
        if work_items:
            ids = [wi["id"] for wi in work_items[:20]]
            details = self.client.get_work_item_details(ids)
            
            answer = f"Found {len(work_items)} user story(ies):\n\n"
            
            for item in details[:10]:
                fields = item.get("fields", {})
                answer += f"• #{item['id']}: {fields.get('System.Title', 'No title')}\n"
                answer += f"  State: {fields.get('System.State', 'Unknown')}"
                if 'Microsoft.VSTS.Common.Priority' in fields:
                    answer += f" | Priority: {fields['Microsoft.VSTS.Common.Priority']}"
                answer += "\n\n"
            
            return {
                "answer": answer,
                "query_type": "user_stories",
                "items_found": len(work_items),
                "api_calls": 2
            }
        else:
            return {
                "answer": "No user stories found.",
                "query_type": "user_stories",
                "items_found": 0,
                "api_calls": 1
            }
    
    def _query_completed_items(self, query: str) -> Dict:
        """Query completed/closed items"""
        
        # Determine time range
        if "week" in query:
            days = 7
        elif "month" in query:
            days = 30
        elif "today" in query:
            days = 1
        else:
            days = 7  # Default to last week
        
        wiql = f"""
        SELECT [System.Id], [System.Title], [System.WorkItemType], [System.ClosedDate]
        FROM WorkItems
        WHERE [System.TeamProject] = '{self.client.project}'
        AND [System.State] IN ('Closed', 'Done', 'Resolved')
        AND [System.ClosedDate] >= @Today - {days}
        ORDER BY [System.ClosedDate] DESC
        """
        
        result = self.client.get_work_items(wiql)
        
        if "error" in result:
            return {
                "answer": f"Failed to query completed items: {result['error']}",
                "query_type": "completed",
                "items_found": 0,
                "api_calls": 1
            }
        
        work_items = result.get("workItems", [])
        
        if work_items:
            ids = [wi["id"] for wi in work_items[:30]]
            details = self.client.get_work_item_details(ids)
            
            # Group by type
            by_type = {}
            for item in details:
                fields = item.get("fields", {})
                wi_type = fields.get("System.WorkItemType", "Unknown")
                if wi_type not in by_type:
                    by_type[wi_type] = []
                by_type[wi_type].append(item)
            
            answer = f"Completed in the last {days} day(s): {len(work_items)} item(s)\n\n"
            
            for wi_type, items in by_type.items():
                answer += f"{wi_type}s ({len(items)}):\n"
                for item in items[:3]:
                    fields = item.get("fields", {})
                    answer += f"• #{item['id']}: {fields.get('System.Title', 'No title')}\n"
                answer += "\n"
            
            return {
                "answer": answer,
                "query_type": "completed",
                "items_found": len(work_items),
                "api_calls": 2
            }
        else:
            return {
                "answer": f"No items completed in the last {days} day(s).",
                "query_type": "completed",
                "items_found": 0,
                "api_calls": 1
            }
    
    def _query_all_work_items(self) -> Dict:
        """Generic query for all active work items"""
        wiql = f"""
        SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State]
        FROM WorkItems
        WHERE [System.TeamProject] = '{self.client.project}'
        AND [System.State] NOT IN ('Closed', 'Done', 'Removed', 'Resolved')
        ORDER BY [System.ChangedDate] DESC
        """
        
        result = self.client.get_work_items(wiql)
        
        if "error" in result:
            return {
                "answer": f"Failed to query work items: {result['error']}",
                "query_type": "all",
                "items_found": 0,
                "api_calls": 1
            }
        
        work_items = result.get("workItems", [])
        
        if work_items:
            ids = [wi["id"] for wi in work_items[:30]]
            details = self.client.get_work_item_details(ids)
            
            # Group by type
            by_type = {}
            for item in details:
                fields = item.get("fields", {})
                wi_type = fields.get("System.WorkItemType", "Unknown")
                if wi_type not in by_type:
                    by_type[wi_type] = 0
                by_type[wi_type] += 1
            
            answer = f"Active work items in project: {len(work_items)}\n\n"
            answer += "Breakdown by type:\n"
            for wi_type, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
                answer += f"• {wi_type}: {count}\n"
            
            answer += f"\nShowing recent items:\n"
            for item in details[:5]:
                fields = item.get("fields", {})
                answer += f"• #{item['id']}: {fields.get('System.Title', 'No title')} [{fields.get('System.WorkItemType', 'Unknown')}]\n"
            
            return {
                "answer": answer,
                "query_type": "all",
                "items_found": len(work_items),
                "api_calls": 2
            }
        else:
            return {
                "answer": "No active work items found in the project.",
                "query_type": "all",
                "items_found": 0,
                "api_calls": 1
            }

@app.get("/")
def read_root():
    return {
        "status": "ADO Assistant API Running",
        "model_loaded": model_loaded,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/test-connection")
async def test_connection(config: ADOConfig):
    """Test connection to Azure DevOps"""
    client = ADOClient(config.organization, config.project, config.pat)
    return client.test_connection()

@app.post("/query")
async def process_query(request: QueryRequest):
    """Process a natural language query about ADO project"""
    
    try:
        # Create ADO client
        client = ADOClient(
            request.config.organization,
            request.config.project,
            request.config.pat
        )
        
        # Process the query
        processor = QueryProcessor(client)
        result = processor.process_query(request.query)
        
        # Add timestamp
        result["timestamp"] = datetime.now().isoformat()
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
