"""
FastAPI backend for SRE Autonomous Agent UI

Provides REST API endpoints for the web interface.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import os
from pathlib import Path
from datetime import datetime
from uuid import uuid4

from app.graph.graph import create_incident_response_app
from app.graph.state import create_initial_state
from app.approval import get_approval_manager, ApprovalStatus
from app.tools.remediation_executor import RemediationExecutor

app = FastAPI(
    title="SRE Autonomous Agent API",
    description="REST API for incident response automation",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Alert(BaseModel):
    """Alert model"""
    status: str = "firing"
    commonLabels: Dict[str, str]
    commonAnnotations: Dict[str, str]
    startsAt: Optional[str] = None


class IncidentResponse(BaseModel):
    """Incident response model"""
    incident_id: str
    status: str
    message: str


class ApprovalAction(BaseModel):
    """Approval action model"""
    approved_by: str = "api-user"
    comment: Optional[str] = None
    reason: Optional[str] = None


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "SRE Autonomous Agent API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/alerts", response_model=IncidentResponse)
async def create_alert(alert: Alert, background_tasks: BackgroundTasks):
    """
    Create and process a new alert
    
    This endpoint receives an alert, generates an incident ID,
    and triggers the autonomous agent workflow.
    """
    try:
        # Generate incident ID
        incident_id = f"INC-{datetime.utcnow().strftime('%Y%m%d')}-{uuid4().hex[:8]}"
        
        # Save alert to file
        alerts_dir = Path("alerts")
        alerts_dir.mkdir(exist_ok=True)
        
        alert_file = alerts_dir / f"{incident_id}.json"
        with open(alert_file, 'w') as f:
            json.dump(alert.dict(), f, indent=2)
        
        # Process in background
        background_tasks.add_task(process_incident, alert.dict(), incident_id)
        
        return IncidentResponse(
            incident_id=incident_id,
            status="processing",
            message=f"Alert received. Incident {incident_id} is being processed."
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def process_incident(alert_payload: dict, incident_id: str):
    """
    Process incident in background
    """
    try:
        # Create initial state
        initial_state = create_initial_state(alert_payload, incident_id)
        
        # Create and run workflow
        app_graph = create_incident_response_app()
        config = {"configurable": {"thread_id": incident_id}}
        
        result = app_graph.invoke(initial_state, config)
        
        # Save postmortem
        save_postmortem(incident_id, result)
        
    except Exception as e:
        print(f"Error processing incident {incident_id}: {e}")


def save_postmortem(incident_id: str, result: dict):
    """Save postmortem to file"""
    postmortem_dir = Path("postmortems")
    postmortem_dir.mkdir(exist_ok=True)
    
    postmortem_file = postmortem_dir / f"{incident_id}.md"
    
    # Extract postmortem content
    postmortem_content = result.get("postmortem", "")
    
    with open(postmortem_file, 'w') as f:
        f.write(postmortem_content)


@app.get("/api/incidents")
async def list_incidents():
    """
    List all incidents with their postmortems
    """
    postmortem_dir = Path("postmortems")
    if not postmortem_dir.exists():
        return []
    
    incidents = []
    for file in postmortem_dir.glob("*.md"):
        with open(file, 'r') as f:
            content = f.read()
        
        incidents.append({
            "incident_id": file.stem,
            "timestamp": datetime.fromtimestamp(file.stat().st_mtime).isoformat(),
            "postmortem": content
        })
    
    return sorted(incidents, key=lambda x: x['timestamp'], reverse=True)


@app.get("/api/incidents/{incident_id}")
async def get_incident(incident_id: str):
    """
    Get specific incident details
    """
    postmortem_file = Path("postmortems") / f"{incident_id}.md"
    
    if not postmortem_file.exists():
        raise HTTPException(status_code=404, detail="Incident not found")
    
    with open(postmortem_file, 'r') as f:
        content = f.read()
    
    return {
        "incident_id": incident_id,
        "timestamp": datetime.fromtimestamp(postmortem_file.stat().st_mtime).isoformat(),
        "postmortem": content
    }


@app.get("/api/stats")
async def get_stats():
    """
    Get system statistics
    """
    postmortem_dir = Path("postmortems")
    
    if not postmortem_dir.exists():
        return {
            "total_incidents": 0,
            "incidents_today": 0,
            "active_incidents": 0
        }
    
    total = len(list(postmortem_dir.glob("*.md")))
    
    # Count today's incidents
    today = datetime.utcnow().date()
    today_count = 0
    
    for file in postmortem_dir.glob("*.md"):
        file_date = datetime.fromtimestamp(file.stat().st_mtime).date()
        if file_date == today:
            today_count += 1
    
    return {
        "total_incidents": total,
        "incidents_today": today_count,
        "active_incidents": 0  # TODO: Track active incidents
    }


@app.get("/api/alerts/examples")
async def get_example_alerts():
    """
    Get example alert templates
    """
    examples_dir = Path("examples")
    if not examples_dir.exists():
        return []
    
    examples = []
    for file in examples_dir.glob("*.json"):
        with open(file, 'r') as f:
            examples.append({
                "name": file.stem,
                "template": json.load(f)
            })
    
    return examples


@app.get("/api/approvals")
async def list_approvals(status: Optional[str] = None):
    """
    List approval requests
    
    Query params:
    - status: Filter by status (pending, approved, rejected)
    """
    try:
        approval_manager = get_approval_manager()
        
        if status == "pending" or status is None:
            # Get pending approvals
            pending = approval_manager.list_pending()
            return [{
                "approval_id": r.approval_id,
                "incident_id": r.incident_id,
                "root_cause": r.root_cause,
                "remediation_action": r.remediation_action,
                "risk_level": r.risk_level,
                "status": r.status.value,
                "created_at": r.created_at
            } for r in pending]
        
        # Load all approvals and filter by status
        approvals_dir = Path("approvals")
        if not approvals_dir.exists():
            return []
        
        results = []
        for file in approvals_dir.glob("*.json"):
            with open(file) as f:
                data = json.load(f)
                if status is None or data.get("status") == status:
                    results.append(data)
        
        return sorted(results, key=lambda x: x.get("created_at", ""), reverse=True)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/approvals/{incident_id}")
async def get_approval(incident_id: str):
    """
    Get approval request for a specific incident
    """
    try:
        approval_file = Path("approvals") / f"{incident_id}.json"
        
        if not approval_file.exists():
            raise HTTPException(status_code=404, detail="Approval request not found")
        
        with open(approval_file) as f:
            data = json.load(f)
        
        return data
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/approvals/{incident_id}/approve")
async def approve_remediation(incident_id: str, action: ApprovalAction):
    """
    Approve a remediation action
    
    This will:
    1. Mark the approval as approved
    2. Execute the remediation
    3. Return the execution result
    """
    try:
        approval_manager = get_approval_manager()
        executor = RemediationExecutor()
        
        # Get the approval request
        pending = approval_manager.list_pending()
        request = next((r for r in pending if r.incident_id == incident_id), None)
        
        if not request:
            raise HTTPException(status_code=404, detail="No pending approval found for this incident")
        
        # Approve the remediation
        approval_manager.approve(
            incident_id,
            action.approved_by,
            action.comment
        )
        
        # Execute the remediation
        success, message = executor.execute_remediation(
            incident_id,
            request.remediation_plan,
            request.alert_data
        )
        
        return {
            "incident_id": incident_id,
            "status": "approved",
            "execution_success": success,
            "execution_message": message,
            "approved_by": action.approved_by,
            "approved_at": datetime.utcnow().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/approvals/{incident_id}/reject")
async def reject_remediation(incident_id: str, action: ApprovalAction):
    """
    Reject a remediation action
    """
    try:
        if not action.reason:
            raise HTTPException(status_code=400, detail="Rejection reason is required")
        
        approval_manager = get_approval_manager()
        
        # Get the approval request
        pending = approval_manager.list_pending()
        request = next((r for r in pending if r.incident_id == incident_id), None)
        
        if not request:
            raise HTTPException(status_code=404, detail="No pending approval found for this incident")
        
        # Reject the remediation
        approval_manager.reject(
            incident_id,
            action.approved_by,
            action.reason
        )
        
        return {
            "incident_id": incident_id,
            "status": "rejected",
            "rejected_by": action.approved_by,
            "rejected_at": datetime.utcnow().isoformat(),
            "reason": action.reason
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
