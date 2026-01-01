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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
