"""
Alertmanager Webhook Server

Receives webhook alerts from Prometheus Alertmanager and triggers
the autonomous incident response workflow.
"""

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4
import uvicorn

from app.graph.graph import create_incident_response_app
from app.graph.state import create_initial_state
from app.integrations.slack import notify_incident

app = FastAPI(
    title="SRE Agent Webhook Server",
    description="Receives alerts from Prometheus Alertmanager",
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


class AlertmanagerAlert(BaseModel):
    """Single alert from Alertmanager"""
    status: str
    labels: Dict[str, str]
    annotations: Dict[str, str]
    startsAt: str
    endsAt: Optional[str] = None
    generatorURL: Optional[str] = None
    fingerprint: Optional[str] = None


class AlertmanagerWebhook(BaseModel):
    """Alertmanager webhook payload"""
    version: str = "4"
    groupKey: str
    status: str
    receiver: str
    groupLabels: Dict[str, str]
    commonLabels: Dict[str, str]
    commonAnnotations: Dict[str, str]
    externalURL: str
    alerts: List[AlertmanagerAlert]


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "SRE Agent Webhook Server",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "alertmanager": "/webhook/alertmanager",
            "pagerduty": "/webhook/pagerduty",
            "generic": "/webhook/alert"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.post("/webhook/alertmanager")
async def alertmanager_webhook(
    webhook: AlertmanagerWebhook,
    background_tasks: BackgroundTasks
):
    """
    Receive webhook from Prometheus Alertmanager
    
    This endpoint processes Alertmanager webhook payloads and triggers
    the autonomous incident response workflow for firing alerts.
    """
    try:
        print(f"\n{'='*80}")
        print(f"Received Alertmanager webhook: {webhook.groupKey}")
        print(f"Status: {webhook.status}")
        print(f"Alerts: {len(webhook.alerts)}")
        print(f"{'='*80}\n")
        
        # Only process firing alerts
        firing_alerts = [a for a in webhook.alerts if a.status == "firing"]
        
        if not firing_alerts:
            return {
                "message": "No firing alerts to process",
                "status": "skipped"
            }
        
        # Process each firing alert
        incident_ids = []
        
        for alert in firing_alerts:
            # Generate incident ID
            incident_id = f"INC-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid4().hex[:8]}"
            
            # Convert to our alert format
            alert_payload = convert_alertmanager_to_alert(webhook, alert)
            
            # Save alert
            save_alert(alert_payload, incident_id)
            
            # Process in background
            background_tasks.add_task(
                process_incident_from_webhook,
                alert_payload,
                incident_id,
                "alertmanager"
            )
            
            incident_ids.append(incident_id)
            
            # Send Slack notification if configured
            try:
                notify_incident(
                    incident_id,
                    alert.labels.get("alertname", "Unknown"),
                    alert.labels.get("severity", "warning")
                )
            except Exception as e:
                print(f"Failed to send Slack notification: {e}")
        
        return {
            "message": f"Processing {len(firing_alerts)} alerts",
            "incident_ids": incident_ids,
            "status": "processing"
        }
    
    except Exception as e:
        print(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhook/pagerduty")
async def pagerduty_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Receive webhook from PagerDuty
    
    Processes PagerDuty incident webhooks and triggers incident response.
    """
    try:
        payload = await request.json()
        
        print(f"\n{'='*80}")
        print("Received PagerDuty webhook")
        print(f"{'='*80}\n")
        
        messages = payload.get("messages", [])
        incident_ids = []
        
        for message in messages:
            # Only process triggered incidents
            if message.get("event") != "incident.trigger":
                continue
            
            incident = message.get("incident", {})
            
            # Generate incident ID
            incident_id = f"INC-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid4().hex[:8]}"
            
            # Convert to our alert format
            alert_payload = convert_pagerduty_to_alert(incident)
            
            # Save alert
            save_alert(alert_payload, incident_id)
            
            # Process in background
            background_tasks.add_task(
                process_incident_from_webhook,
                alert_payload,
                incident_id,
                "pagerduty"
            )
            
            incident_ids.append(incident_id)
        
        return {
            "message": f"Processing {len(incident_ids)} incidents",
            "incident_ids": incident_ids,
            "status": "processing"
        }
    
    except Exception as e:
        print(f"Error processing PagerDuty webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhook/alert")
async def generic_alert_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Generic alert webhook endpoint
    
    Accepts alerts in the standard format used by the agent.
    """
    try:
        alert_payload = await request.json()
        
        # Generate incident ID
        incident_id = f"INC-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid4().hex[:8]}"
        
        # Save alert
        save_alert(alert_payload, incident_id)
        
        # Process in background
        background_tasks.add_task(
            process_incident_from_webhook,
            alert_payload,
            incident_id,
            "generic"
        )
        
        return {
            "message": "Alert received and processing",
            "incident_id": incident_id,
            "status": "processing"
        }
    
    except Exception as e:
        print(f"Error processing generic alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def convert_alertmanager_to_alert(
    webhook: AlertmanagerWebhook,
    alert: AlertmanagerAlert
) -> Dict[str, Any]:
    """Convert Alertmanager alert to our standard format"""
    return {
        "status": alert.status,
        "commonLabels": {
            **webhook.commonLabels,
            **alert.labels,
            "alertname": alert.labels.get("alertname", "Unknown"),
            "severity": alert.labels.get("severity", "warning"),
            "namespace": alert.labels.get("namespace", "default"),
            "pod": alert.labels.get("pod", alert.labels.get("pod_name", "")),
            "deployment": alert.labels.get("deployment", ""),
            "container": alert.labels.get("container", "")
        },
        "commonAnnotations": {
            **webhook.commonAnnotations,
            **alert.annotations,
            "summary": alert.annotations.get("summary", alert.annotations.get("description", "")),
            "description": alert.annotations.get("description", "")
        },
        "startsAt": alert.startsAt,
        "endsAt": alert.endsAt,
        "generatorURL": alert.generatorURL,
        "fingerprint": alert.fingerprint
    }


def convert_pagerduty_to_alert(incident: Dict[str, Any]) -> Dict[str, Any]:
    """Convert PagerDuty incident to our standard format"""
    return {
        "status": "firing",
        "commonLabels": {
            "alertname": incident.get("title", "PagerDuty Incident"),
            "severity": "critical" if incident.get("urgency") == "high" else "warning",
            "source": "pagerduty",
            "incident_key": incident.get("incident_key", ""),
            "service": incident.get("service", {}).get("name", "")
        },
        "commonAnnotations": {
            "summary": incident.get("title", ""),
            "description": incident.get("body", {}).get("details", ""),
            "incident_url": incident.get("html_url", "")
        },
        "startsAt": incident.get("created_at", datetime.now(timezone.utc).isoformat())
    }


def save_alert(alert_data: Dict[str, Any], incident_id: str):
    """Save alert to file"""
    alerts_dir = Path("alerts")
    alerts_dir.mkdir(exist_ok=True)
    
    alert_file = alerts_dir / f"{incident_id}.json"
    with open(alert_file, 'w') as f:
        json.dump(alert_data, f, indent=2)
    
    print(f"Saved alert to {alert_file}")


def process_incident_from_webhook(
    alert_payload: Dict[str, Any],
    incident_id: str,
    source: str
):
    """
    Process incident in background
    """
    try:
        print(f"\n{'='*80}")
        print(f"Processing incident {incident_id} from {source}")
        print(f"{'='*80}\n")
        
        # Create initial state
        initial_state = create_initial_state(alert_payload, incident_id)
        
        # Create and run workflow
        app_graph = create_incident_response_app()
        config = {"configurable": {"thread_id": incident_id}}
        
        result = app_graph.invoke(initial_state, config)
        
        # Save postmortem
        save_postmortem(incident_id, result)
        
        print(f"\n{'='*80}")
        print(f"Completed processing incident {incident_id}")
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"Error processing incident {incident_id}: {e}")
        import traceback
        traceback.print_exc()


def save_postmortem(incident_id: str, result: Dict[str, Any]):
    """Save postmortem to file"""
    postmortem_dir = Path("postmortems")
    postmortem_dir.mkdir(exist_ok=True)
    
    postmortem_file = postmortem_dir / f"{incident_id}.md"
    
    # Extract postmortem content
    postmortem_content = result.get("postmortem", "")
    
    with open(postmortem_file, 'w') as f:
        f.write(postmortem_content)
    
    print(f"Saved postmortem to {postmortem_file}")


def start_webhook_server(host: str = "0.0.0.0", port: int = 9000):
    """
    Start the webhook server
    
    Args:
        host: Host to bind to (default: 0.0.0.0)
        port: Port to listen on (default: 9000)
    """
    print(f"\n{'='*80}")
    print("Starting SRE Agent Webhook Server")
    print(f"{'='*80}")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print("\nEndpoints:")
    print(f"  - Alertmanager: http://{host}:{port}/webhook/alertmanager")
    print(f"  - PagerDuty:    http://{host}:{port}/webhook/pagerduty")
    print(f"  - Generic:      http://{host}:{port}/webhook/alert")
    print(f"  - Health:       http://{host}:{port}/health")
    print(f"{'='*80}\n")
    
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    # Get host and port from environment or use defaults
    host = os.getenv("WEBHOOK_HOST", "0.0.0.0")
    port = int(os.getenv("WEBHOOK_PORT", "9000"))
    
    start_webhook_server(host, port)
