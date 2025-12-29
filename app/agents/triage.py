"""
Triage Agent

Responsibilities:
- Classify incident type from alert
- Extract affected resources
- Determine severity
- NO speculation, only classification
"""

from typing import Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.graph.state import IncidentState, add_timeline_entry


TRIAGE_SYSTEM_PROMPT = """You are a Kubernetes SRE triage specialist.

Your ONLY job is to:
1. Classify the incident type based on the alert
2. Extract affected resources (namespace, pod, deployment, etc.)
3. Assign severity based on alert labels and known patterns

Common incident types:
- CrashLoopBackOff: Container keeps restarting
- OOMKilled: Out of memory
- ImagePullBackOff: Cannot pull container image
- NodeNotReady: Node health issue
- PodPending: Pod stuck in pending state
- HighErrorRate: Application errors elevated
- HighLatency: Response time degraded

Rules:
- Be precise, no speculation
- Use exact alert labels
- If unclear, classify as "Unknown" and explain why
- Extract all relevant resource identifiers

Output JSON format:
{
    "incident_type": "CrashLoopBackOff",
    "severity": "critical",
    "affected_resources": {
        "namespace": "payments",
        "pod": "api-7c9d4f-xyz",
        "deployment": "api",
        "container": "api-server"
    },
    "reasoning": "Alert indicates pod restart loop with 12 restarts"
}
"""


def triage_agent(state: IncidentState) -> IncidentState:
    """
    Classify the incident and extract key metadata
    """
    
    alert = state["alert"]
    
    # Build context from alert
    alert_context = f"""
Alert Data:
- Name: {alert.get('commonLabels', {}).get('alertname', 'Unknown')}
- Status: {alert.get('status', 'Unknown')}
- Labels: {alert.get('commonLabels', {})}
- Annotations: {alert.get('commonAnnotations', {})}

Full Alert Details:
{alert}

Classify this incident precisely.
"""
    
    # Use LLM for classification
    llm = ChatOpenAI(model="gpt-4", temperature=0)
    
    messages = [
        SystemMessage(content=TRIAGE_SYSTEM_PROMPT),
        HumanMessage(content=alert_context)
    ]
    
    response = llm.invoke(messages)
    
    # Parse response (simplified - add proper JSON parsing)
    # For MVP, assume structured output
    result = eval(response.content)  # TODO: Use proper JSON parsing
    
    # Update state
    state["incident_type"] = result["incident_type"]
    state["severity"] = result["severity"]
    state["affected_resources"] = result["affected_resources"]
    
    # Add timeline
    state = add_timeline_entry(
        state,
        agent="triage",
        action="classified",
        details=f"Incident type: {result['incident_type']}, Severity: {result['severity']}"
    )
    
    return state
