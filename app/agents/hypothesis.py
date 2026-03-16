"""
Hypothesis Agent

Responsibilities:
- Generate ranked hypotheses about root cause
- Pure reasoning, NO tool usage
- Based on incident type and context
"""

import json

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

from app.graph.state import IncidentState, Hypothesis, add_timeline_entry

# Load environment variables
load_dotenv()


HYPOTHESIS_SYSTEM_PROMPT = """You are a Kubernetes SRE diagnostic specialist.

Given an incident type and context, generate 3-5 ranked hypotheses about the root cause.

For CrashLoopBackOff, common causes:
1. Missing/incorrect environment variables
2. Failed readiness/liveness probes
3. Application startup errors
4. Recent deployment regression
5. Resource constraints (CPU/memory limits)
6. Config/secret mounting issues
7. Dependency service unavailable

Rules:
- Rank by likelihood (most likely first)
- Assign confidence score (0.0 to 1.0)
- Categorize: "config", "resource", "network", "code", "infra"
- Be specific, not generic
- Consider recent changes if known

Output JSON format:
[
    {
        "description": "Container exits due to missing DATABASE_URL env variable",
        "confidence": 0.8,
        "category": "config"
    },
    {
        "description": "Readiness probe failing on /health endpoint",
        "confidence": 0.6,
        "category": "code"
    }
]
"""


def hypothesis_agent(state: IncidentState) -> IncidentState:
    """
    Generate ranked hypotheses about the root cause
    """
    
    incident_type = state["incident_type"]
    affected_resources = state["affected_resources"]
    alert = state["alert"]
    
    context = f"""
Incident Type: {incident_type}
Severity: {state['severity']}

Affected Resources:
{affected_resources}

Alert Annotations:
{alert.get('commonAnnotations', {})}

Generate hypotheses for this incident.
"""
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
    
    messages = [
        SystemMessage(content=HYPOTHESIS_SYSTEM_PROMPT),
        HumanMessage(content=context)
    ]
    
    response = llm.invoke(messages)
    
    # Parse response
    try:
        response_text = response.content
        # Find JSON array
        start = response_text.find('[')
        end = response_text.rfind(']') + 1
        if start >= 0 and end > start:
            json_text = response_text[start:end]
            hypotheses_data = json.loads(json_text)
        else:
            # Fallback
            hypotheses_data = [
                {
                    "description": "Analysis needed - see alert details",
                    "confidence": 0.5,
                    "category": "unknown"
                }
            ]
    except Exception as e:
        hypotheses_data = [
            {
                "description": f"Parse error: {str(e)}",
                "confidence": 0.3,
                "category": "error"
            }
        ]
    
    hypotheses = [
        Hypothesis(
            description=h["description"],
            confidence=h["confidence"],
            category=h["category"]
        )
        for h in hypotheses_data
    ]
    
    state["hypotheses"] = hypotheses
    
    state = add_timeline_entry(
        state,
        agent="hypothesis",
        action="generated_hypotheses",
        details=f"Generated {len(hypotheses)} hypotheses, top: {hypotheses[0]['description']}"
    )
    
    return state
