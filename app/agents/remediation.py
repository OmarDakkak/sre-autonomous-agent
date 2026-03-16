"""
Remediation Planner Agent

Responsibilities:
- Propose safe remediation actions
- NO execution (that requires approval)
- Generate PR-based fixes when appropriate
- Assess risk and blast radius
"""

import json
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import yaml
from dotenv import load_dotenv

from app.graph.state import IncidentState, RemediationAction, add_timeline_entry

# Load environment variables
load_dotenv()

_GUARDRAILS_PATH = Path(__file__).parent.parent / "policies" / "guardrails.yaml"


REMEDIATION_SYSTEM_PROMPT = """You are a Kubernetes SRE remediation specialist.

Your job:
1. Propose a PRIMARY remediation action
2. Suggest 1-2 alternative approaches
3. Assess risk for each
4. Determine if PR is required

Common remediations for CrashLoopBackOff:
- Add missing env variable (requires PR)
- Fix probe configuration (requires PR)
- Rollback to previous deployment
- Adjust resource limits (requires PR)
- Restart deployment (immediate, low risk)

Risk Assessment:
- LOW: Read-only, restart, non-destructive scale
- MEDIUM: Config changes, rollback
- HIGH: Deletion, major changes, prod writes

PR Requirements:
- Config/manifest changes → requires PR
- Immediate actions (restart) → no PR needed

Output JSON format:
{
    "primary": {
        "action_type": "config_change",
        "description": "Add DATABASE_URL to deployment env",
        "risk_level": "low",
        "requires_pr": true,
        "command": "kubectl set env deployment/api DATABASE_URL=...",
        "estimated_impact": "Resolves crash, requires pod restart"
    },
    "alternatives": [
        {
            "action_type": "rollback",
            "description": "Rollback to previous deployment version",
            "risk_level": "medium",
            "requires_pr": false,
            "command": "kubectl rollout undo deployment/api",
            "estimated_impact": "Immediate fix, loses new features"
        }
    ]
}
"""


def load_guardrails():
    """Load guardrails policy"""
    with open(_GUARDRAILS_PATH, "r") as f:
        return yaml.safe_load(f)


def validate_against_guardrails(action: RemediationAction) -> tuple[bool, str]:
    """Check if action is allowed by guardrails"""
    guardrails = load_guardrails()
    
    # Check forbidden actions
    forbidden = guardrails.get("forbidden_actions", [])
    action_type = action["action_type"]
    
    if action_type in forbidden:
        return False, f"Action '{action_type}' is forbidden by guardrails"
    
    # Check namespace permissions
    # TODO: Add more validation logic
    
    return True, "Action complies with guardrails"


def remediation_agent(state: IncidentState) -> IncidentState:
    """
    Plan safe remediation actions
    """
    
    root_cause = state["root_cause"]
    incident_type = state["incident_type"]
    affected_resources = state["affected_resources"]
    
    context = f"""
Incident Type: {incident_type}
Root Cause: {root_cause}

Affected Resources:
{affected_resources}

Diagnostics Summary:
{state['diagnostics'][-1] if state['diagnostics'] else 'None'}

Propose remediation actions.
"""
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    messages = [
        SystemMessage(content=REMEDIATION_SYSTEM_PROMPT),
        HumanMessage(content=context)
    ]
    
    response = llm.invoke(messages)
    
    # Parse response
    try:
        response_text = response.content
        # Find JSON block
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        if start >= 0 and end > start:
            json_text = response_text[start:end]
            plan_data = json.loads(json_text)
        else:
            raise ValueError("No JSON found in response")
    except Exception as e:
        # Fallback plan
        plan_data = {
            "primary": {
                "action_type": "manual_investigation",
                "description": f"Manual investigation required. Parse error: {str(e)}",
                "risk_level": "low",
                "requires_pr": False,
                "estimated_impact": "Requires human analysis"
            },
            "alternatives": []
        }
    
    primary = RemediationAction(
        action_type=plan_data["primary"]["action_type"],
        description=plan_data["primary"]["description"],
        risk_level=plan_data["primary"]["risk_level"],
        requires_pr=plan_data["primary"]["requires_pr"],
        command=plan_data["primary"].get("command"),
        estimated_impact=plan_data["primary"]["estimated_impact"]
    )
    
    # Validate against guardrails
    is_valid, validation_msg = validate_against_guardrails(primary)
    
    if not is_valid:
        state["errors"].append(f"Remediation blocked: {validation_msg}")
        return state
    
    state["remediation_plan"] = primary
    
    # Add alternatives
    alternatives = [
        RemediationAction(
            action_type=alt["action_type"],
            description=alt["description"],
            risk_level=alt["risk_level"],
            requires_pr=alt["requires_pr"],
            command=alt.get("command"),
            estimated_impact=alt["estimated_impact"]
        )
        for alt in plan_data.get("alternatives", [])
    ]
    
    state["alternative_plans"] = alternatives
    
    state = add_timeline_entry(
        state,
        agent="remediation",
        action="plan_created",
        details=f"Primary action: {primary['description']}, Risk: {primary['risk_level']}"
    )
    
    return state
