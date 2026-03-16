"""
LangGraph State Definition for SRE Autonomous Agent

This state flows through all agents, maintaining context and ensuring
auditability and deterministic reasoning.
"""

from typing import TypedDict, Literal, Optional
from datetime import datetime, timezone


class Hypothesis(TypedDict):
    """A potential root cause with confidence scoring"""
    description: str
    confidence: float  # 0.0 to 1.0
    category: str  # e.g., "config", "resource", "network", "code"


class DiagnosticResult(TypedDict):
    """Results from diagnostic tools"""
    source: str  # e.g., "kubectl", "prometheus", "logs"
    data: dict
    timestamp: str


class RemediationAction(TypedDict):
    """A proposed remediation action"""
    action_type: str  # e.g., "restart", "scale", "config_change", "rollback"
    description: str
    risk_level: Literal["low", "medium", "high"]
    requires_pr: bool
    command: Optional[str]
    estimated_impact: str


class TimelineEntry(TypedDict):
    """Audit trail entry"""
    timestamp: str
    agent: str
    action: str
    details: str


class IncidentState(TypedDict):
    """
    Complete state for incident response workflow
    
    This state is passed between all agents and maintains:
    - Alert context
    - Classification results
    - Hypotheses and diagnostics
    - Remediation plans
    - Approval status
    - Full audit trail
    """
    
    # Input: Raw alert data
    alert: dict
    incident_id: str
    
    # Triage Agent outputs
    incident_type: Optional[str]  # e.g., "CrashLoopBackOff", "OOMKilled"
    severity: Optional[str]  # "low", "medium", "high", "critical"
    affected_resources: dict  # namespace, pod, deployment, etc.
    
    # Hypothesis Agent outputs
    hypotheses: list[Hypothesis]
    
    # Diagnostic Agent outputs
    diagnostics: list[DiagnosticResult]
    root_cause: Optional[str]
    
    # Remediation Planner outputs
    remediation_plan: Optional[RemediationAction]
    alternative_plans: list[RemediationAction]
    
    # Human approval checkpoint
    approved: bool
    approval_id: Optional[str]
    approval_comment: Optional[str]
    
    # Execution status (for future auto-fix)
    remediation_executed: bool
    execution_status: Optional[Literal["pending", "running", "success", "failed"]]
    execution_result: Optional[str]
    
    # Postmortem
    postmortem: Optional[str]
    
    # Audit trail
    timeline: list[TimelineEntry]
    
    # Error handling
    errors: list[str]
    
    # Metadata
    started_at: str
    updated_at: str


def create_initial_state(alert: dict, incident_id: str) -> IncidentState:
    """Create initial state from incoming alert"""
    now = datetime.now(timezone.utc).isoformat()
    
    return IncidentState(
        alert=alert,
        incident_id=incident_id,
        incident_type=None,
        severity=None,
        affected_resources={},
        hypotheses=[],
        diagnostics=[],
        root_cause=None,
        remediation_plan=None,
        alternative_plans=[],
        approved=False,
        approval_id=None,
        approval_comment=None,
        remediation_executed=False,
        execution_status=None,
        execution_result=None,
        postmortem=None,
        timeline=[
            TimelineEntry(
                timestamp=now,
                agent="system",
                action="incident_created",
                details=f"Alert received: {alert.get('commonLabels', {}).get('alertname', 'unknown')}"
            )
        ],
        errors=[],
        started_at=now,
        updated_at=now
    )


def add_timeline_entry(
    state: IncidentState,
    agent: str,
    action: str,
    details: str
) -> IncidentState:
    """Helper to add timeline entries"""
    entry = TimelineEntry(
        timestamp=datetime.now(timezone.utc).isoformat(),
        agent=agent,
        action=action,
        details=details
    )
    state["timeline"].append(entry)
    state["updated_at"] = entry["timestamp"]
    return state
