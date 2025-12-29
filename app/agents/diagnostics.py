"""
Diagnostics Agent

Responsibilities:
- Execute safe diagnostic tools
- Gather evidence (logs, events, configs)
- Validate hypotheses
- Determine root cause
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate

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
    
    affected_resources = state["affected_resources"]
    namespace = affected_resources.get("namespace")
    pod_name = affected_resources.get("pod")
    
    if not namespace or not pod_name:
        state["errors"].append("Missing namespace or pod name for diagnostics")
        return state
    
    # Create tool-using agent
    tools = [
        get_pod_description,
        get_pod_logs,
        get_pod_events,
        get_recent_deployments
    ]
    
    llm = ChatOpenAI(model="gpt-4", temperature=0)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", DIAGNOSTICS_SYSTEM_PROMPT),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}")
    ])
    
    agent = create_openai_tools_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    
    # Build diagnostic query
    hypotheses_text = "\n".join([
        f"{i+1}. {h['description']} (confidence: {h['confidence']})"
        for i, h in enumerate(state["hypotheses"][:3])
    ])
    
    query = f"""
Investigate this incident:

Incident Type: {state['incident_type']}
Namespace: {namespace}
Pod: {pod_name}

Top Hypotheses:
{hypotheses_text}

Use the diagnostic tools to:
1. Gather evidence
2. Validate hypotheses
3. Identify the root cause

Be thorough but focused.
"""
    
    result = agent_executor.invoke({"input": query})
    
    # Parse result (simplified)
    root_cause_data = eval(result["output"])  # TODO: Proper parsing
    
    state["root_cause"] = root_cause_data["root_cause"]
    
    # Store diagnostics (simplified - should capture all tool outputs)
    state["diagnostics"].append(
        DiagnosticResult(
            source="agent_investigation",
            data=root_cause_data,
            timestamp=state["updated_at"]
        )
    )
    
    state = add_timeline_entry(
        state,
        agent="diagnostics",
        action="root_cause_identified",
        details=f"Root cause: {state['root_cause']}"
    )
    
    return state
