"""
Diagnostics Agent

Responsibilities:
- Execute safe diagnostic tools
- Gather evidence (logs, events, configs)
- Validate hypotheses
- Determine root cause
"""

import json

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

from app.graph.state import IncidentState, DiagnosticResult, add_timeline_entry
from app.tools.kubernetes import (
    get_pod_description,
    get_pod_logs,
    get_pod_events,
    get_recent_deployments
)


DIAGNOSTICS_SYSTEM_PROMPT = """You are a Kubernetes SRE diagnostics specialist.

Your job:
1. Use available tools to gather evidence
2. Validate the top hypotheses
3. Identify the root cause with confidence

Available Tools:
- get_pod_description: Get full pod YAML and status
- get_pod_logs: Get recent container logs
- get_pod_events: Get Kubernetes events for the pod
- get_recent_deployments: Check recent deployment history

For CrashLoopBackOff:
1. Check pod events for restart reasons
2. Get last 100 log lines
3. Check exit code and termination reason
4. Look for probe failures
5. Check recent deployment changes

Be methodical. Gather evidence before concluding.

When you have enough evidence, output:
{
    "root_cause": "Clear, specific root cause",
    "evidence": ["Evidence point 1", "Evidence point 2"],
    "confidence": 0.95
}
"""


def diagnostics_agent(state: IncidentState) -> IncidentState:
    """
    Run diagnostics to identify root cause
    """
    
    # Load environment variables
    load_dotenv()

    affected_resources = state["affected_resources"]
    namespace = affected_resources.get("namespace")
    pod_name = affected_resources.get("pod")
    
    if not namespace or not pod_name:
        state["errors"].append("Missing namespace or pod name for diagnostics")
        return state
    
    # Initialize LLM
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    # Gather diagnostic data directly
    try:
        # Get pod description
        pod_desc = get_pod_description.invoke({"namespace": namespace, "pod_name": pod_name})
        
        # Get pod logs
        pod_logs = get_pod_logs.invoke({"namespace": namespace, "pod_name": pod_name, "tail_lines": 100})
        
        # Get pod events
        pod_events = get_pod_events.invoke({"namespace": namespace, "pod_name": pod_name})
        
        # Get deployment history
        deployment_name = affected_resources.get("deployment", "")
        deployment_history = ""
        if deployment_name:
            deployment_history = get_recent_deployments.invoke({
                "namespace": namespace,
                "deployment_name": deployment_name,
                "limit": 3
            })
        
        # Store all diagnostic results
        state["diagnostics"].append(
            DiagnosticResult(
                source="pod_description",
                data={"output": pod_desc},
                timestamp=state["updated_at"]
            )
        )
        state["diagnostics"].append(
            DiagnosticResult(
                source="pod_logs",
                data={"output": pod_logs},
                timestamp=state["updated_at"]
            )
        )
        state["diagnostics"].append(
            DiagnosticResult(
                source="pod_events",
                data={"output": pod_events},
                timestamp=state["updated_at"]
            )
        )
        
        # Build diagnostic summary for LLM analysis
        hypotheses_text = "\n".join([
            f"{i+1}. {h['description']} (confidence: {h['confidence']})"
            for i, h in enumerate(state["hypotheses"][:3])
        ])
        
        analysis_prompt = f"""
Analyze this Kubernetes incident and identify the root cause:

Incident Type: {state['incident_type']}
Namespace: {namespace}
Pod: {pod_name}

Top Hypotheses:
{hypotheses_text}

Pod Description:
{pod_desc[:2000]}

Pod Logs:
{pod_logs[:2000]}

Pod Events:
{pod_events[:1000]}

Deployment History:
{deployment_history[:1000] if deployment_history else "Not available"}

Based on this evidence, provide:
1. The root cause (be specific)
2. Key evidence supporting this conclusion
3. Confidence level (0.0 to 1.0)

Output as JSON:
{{
    "root_cause": "specific root cause",
    "evidence": ["evidence 1", "evidence 2"],
    "confidence": 0.95
}}
"""
        
        messages = [
            SystemMessage(content=DIAGNOSTICS_SYSTEM_PROMPT),
            HumanMessage(content=analysis_prompt)
        ]
        
        response = llm.invoke(messages)
        
        # Parse the response
        try:
            # Try to extract JSON from response
            response_text = response.content
            # Find JSON block
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start >= 0 and end > start:
                json_text = response_text[start:end]
                root_cause_data = json.loads(json_text)
            else:
                # Fallback if no JSON found
                root_cause_data = {
                    "root_cause": response_text[:500],
                    "evidence": ["See diagnostic output"],
                    "confidence": 0.7
                }
        except (json.JSONDecodeError, Exception):
            root_cause_data = {
                "root_cause": response.content[:500],
                "evidence": ["See diagnostic output"],
                "confidence": 0.7
            }
        
        state["root_cause"] = root_cause_data["root_cause"]
        
        state = add_timeline_entry(
            state,
            agent="diagnostics",
            action="root_cause_identified",
            details=f"Root cause: {state['root_cause']}"
        )
        
    except Exception as e:
        state["errors"].append(f"Diagnostic error: {str(e)}")
        return state
    
    return state
