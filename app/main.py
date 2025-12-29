"""
Main entry point for SRE Autonomous Agent

This module provides webhook handlers and CLI interface.
"""

import json
import os
from uuid import uuid4
from datetime import datetime
from pathlib import Path

from app.graph.graph import create_incident_response_app
from app.graph.state import create_initial_state


def handle_alert_webhook(alert_payload: dict) -> dict:
    """
    Handle incoming alert webhook (from Alertmanager, PagerDuty, etc.)
    
    Args:
        alert_payload: Alert data in standard format
        
    Returns:
        Response with incident ID and status
    """
    
    # Generate incident ID
    incident_id = f"INC-{datetime.utcnow().strftime('%Y%m%d')}-{uuid4().hex[:8]}"
    
    print(f"\n🚨 Alert received: {incident_id}")
    print(f"Alert: {alert_payload.get('commonLabels', {}).get('alertname', 'Unknown')}")
    
    # Create initial state
    initial_state = create_initial_state(alert_payload, incident_id)
    
    # Create and run workflow
    app = create_incident_response_app()
    config = {"configurable": {"thread_id": incident_id}}
    
    try:
        result = app.invoke(initial_state, config)
        
        # Save postmortem
        save_postmortem(incident_id, result)
        
        return {
            "status": "success",
            "incident_id": incident_id,
            "incident_type": result.get("incident_type"),
            "root_cause": result.get("root_cause"),
            "remediation_plan": result.get("remediation_plan"),
            "requires_approval": not result.get("approved"),
            "postmortem_path": f"postmortems/{incident_id}.md"
        }
        
    except Exception as e:
        print(f"❌ Error processing alert: {str(e)}")
        return {
            "status": "error",
            "incident_id": incident_id,
            "error": str(e)
        }


def save_postmortem(incident_id: str, state: dict):
    """Save postmortem to file"""
    
    postmortem_dir = Path("postmortems")
    postmortem_dir.mkdir(exist_ok=True)
    
    postmortem_path = postmortem_dir / f"{incident_id}.md"
    
    with open(postmortem_path, "w") as f:
        f.write(state.get("postmortem", "No postmortem generated"))
    
    print(f"\n📝 Postmortem saved: {postmortem_path}")


def run_from_file(alert_file: str):
    """
    Run agent from alert file (for testing/demo)
    
    Args:
        alert_file: Path to JSON alert file
    """
    
    with open(alert_file, "r") as f:
        alert = json.load(f)
    
    result = handle_alert_webhook(alert)
    
    print("\n" + "="*80)
    print("📊 INCIDENT RESPONSE SUMMARY")
    print("="*80)
    print(f"Incident ID: {result['incident_id']}")
    print(f"Status: {result['status']}")
    
    if result['status'] == 'success':
        print(f"Incident Type: {result['incident_type']}")
        print(f"Root Cause: {result['root_cause']}")
        print(f"\nRemediation Plan:")
        print(f"  {result['remediation_plan']['description']}")
        print(f"  Risk: {result['remediation_plan']['risk_level']}")
        print(f"  Requires Approval: {result['requires_approval']}")
        print(f"\nPostmortem: {result['postmortem_path']}")
    else:
        print(f"Error: {result['error']}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m app.main <alert_file.json>")
        print("\nExample:")
        print("  python -m app.main examples/crashloop_alert.json")
        sys.exit(1)
    
    alert_file = sys.argv[1]
    
    if not os.path.exists(alert_file):
        print(f"❌ Alert file not found: {alert_file}")
        sys.exit(1)
    
    run_from_file(alert_file)
