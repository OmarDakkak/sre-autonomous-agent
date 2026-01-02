"""
LangGraph Workflow Definition

This is the core orchestration graph that connects all agents
in a deterministic, auditable flow with human-in-the-loop checkpoints.
"""

from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.graph.state import IncidentState, create_initial_state
from app.agents.triage import triage_agent
from app.agents.hypothesis import hypothesis_agent
from app.agents.diagnostics import diagnostics_agent
from app.agents.remediation import remediation_agent
from app.agents.postmortem import postmortem_agent
from app.approval import get_approval_manager, ApprovalStatus
from app.tools.remediation_executor import RemediationExecutor


def should_continue_after_triage(state: IncidentState) -> Literal["hypothesis", "error"]:
    """Conditional edge: Check if triage succeeded"""
    if state.get("errors") or not state.get("incident_type"):
        return "error"
    return "hypothesis"


def should_continue_after_diagnostics(state: IncidentState) -> Literal["remediation", "error"]:
    """Conditional edge: Check if diagnostics found root cause"""
    if state.get("errors") or not state.get("root_cause"):
        return "error"
    return "remediation"


def should_continue_after_remediation(state: IncidentState) -> Literal["approval", "error"]:
    """Conditional edge: Check if remediation plan was created"""
    if state.get("errors") or not state.get("remediation_plan"):
        return "error"
    return "approval"


def human_approval_node(state: IncidentState) -> IncidentState:
    """
    Human-in-the-loop checkpoint.
    
    Creates an approval request and waits for human approval.
    Once approved, executes the remediation.
    """
    
    approval_manager = get_approval_manager()
    executor = RemediationExecutor()
    
    incident_id = state["incident_id"]
    
    # Check if already approved
    if approval_manager.is_approved(incident_id):
        print(f"\n✓ Remediation already approved for incident {incident_id}")
        
        # Execute the remediation
        success, message = executor.execute_remediation(
            incident_id,
            state["remediation_plan"],
            state["alert"]
        )
        
        state["remediation_executed"] = success
        state["execution_result"] = message
        
        if not success:
            state["errors"].append(f"Remediation execution failed: {message}")
        
        return state
    
    # Create approval request
    approval_id = approval_manager.create_approval_request(
        incident_id=incident_id,
        root_cause=state["root_cause"],
        remediation_action=state["remediation_plan"]["description"],
        risk_level=state["remediation_plan"]["risk_level"],
        alert_data=state["alert"],
        remediation_plan=state["remediation_plan"]
    )
    
    print("\n" + "="*80)
    print("HUMAN APPROVAL REQUIRED")
    print("="*80)
    print(f"\nApproval ID: {approval_id}")
    print(f"Incident: {state['incident_type']}")
    print(f"Root Cause: {state['root_cause']}")
    print(f"\nProposed Remediation:")
    print(f"  Action: {state['remediation_plan']['description']}")
    print(f"  Risk: {state['remediation_plan']['risk_level']}")
    print(f"  Requires PR: {state['remediation_plan']['requires_pr']}")
    if state['remediation_plan'].get('command'):
        print(f"  Command: {state['remediation_plan']['command']}")
    print("\nTo approve, run:")
    print(f"  python -m app.cli.approve {incident_id}")
    print("="*80)
    
    # Mark as pending approval
    state["approved"] = False
    state["approval_id"] = approval_id
    state["remediation_executed"] = False
    
    return state


def error_handler_node(state: IncidentState) -> IncidentState:
    """Handle errors in the workflow"""
    
    print("\nError in incident response workflow:")
    for error in state.get("errors", []):
        print(f"  - {error}")
    
    # Still generate postmortem for audit trail
    return postmortem_agent(state)


def build_incident_response_graph() -> StateGraph:
    """
    Build the complete incident response workflow graph.
    
    Flow:
    Alert → Triage → Hypothesis → Diagnostics → Remediation → Approval → Postmortem
    
    Each node is deterministic and auditable.
    Human approval is required before any execution.
    """
    
    # Initialize graph with our state type
    workflow = StateGraph(IncidentState)
    
    # Add nodes
    workflow.add_node("triage", triage_agent)
    workflow.add_node("hypothesis", hypothesis_agent)
    workflow.add_node("diagnostics", diagnostics_agent)
    workflow.add_node("remediation", remediation_agent)
    workflow.add_node("approval", human_approval_node)
    workflow.add_node("postmortem", postmortem_agent)
    workflow.add_node("error", error_handler_node)
    
    # Set entry point
    workflow.set_entry_point("triage")
    
    # Add edges
    workflow.add_conditional_edges(
        "triage",
        should_continue_after_triage,
        {
            "hypothesis": "hypothesis",
            "error": "error"
        }
    )
    
    workflow.add_edge("hypothesis", "diagnostics")
    
    workflow.add_conditional_edges(
        "diagnostics",
        should_continue_after_diagnostics,
        {
            "remediation": "remediation",
            "error": "error"
        }
    )
    
    workflow.add_conditional_edges(
        "remediation",
        should_continue_after_remediation,
        {
            "approval": "approval",
            "error": "error"
        }
    )
    
    workflow.add_edge("approval", "postmortem")
    workflow.add_edge("postmortem", END)
    workflow.add_edge("error", END)
    
    return workflow


def create_incident_response_app():
    """
    Create the compiled LangGraph application with checkpointing.
    
    Checkpointing enables:
    - State persistence
    - Replay capability
    - HITL breakpoints
    - Audit trail
    """
    
    workflow = build_incident_response_graph()
    
    # Add memory checkpointing (in production, use Redis or DB)
    memory = MemorySaver()
    
    # Compile with checkpointing enabled
    app = workflow.compile(checkpointer=memory)
    
    return app


# Example usage
if __name__ == "__main__":
    import json
    from uuid import uuid4
    
    # Load example alert
    with open("examples/crashloop_alert.json", "r") as f:
        alert = json.load(f)
    
    # Create initial state
    incident_id = str(uuid4())
    initial_state = create_initial_state(alert, incident_id)
    
    # Create app
    app = create_incident_response_app()
    
    # Run workflow
    print(f"\nStarting incident response for: {incident_id}\n")
    
    config = {"configurable": {"thread_id": incident_id}}
    
    result = app.invoke(initial_state, config)
    
    # Print postmortem
    print("\n" + "="*80)
    print("POSTMORTEM")
    print("="*80)
    print(result.get("postmortem", "No postmortem generated"))
