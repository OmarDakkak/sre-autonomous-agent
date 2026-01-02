# SRE Autonomous Agent

An intelligent, agentic SRE system that automatically diagnoses Kubernetes incidents, proposes safe remediations, and generates comprehensive postmortems.

**NOT ChatOps. This is reasoning + action.**

## What It Does

The agent autonomously:

1. **Detects** incidents from alerts (Alertmanager, PagerDuty, etc.)
2. **Triages** incident type and severity
3. **Forms hypotheses** about root causes
4. **Runs diagnostics** (kubectl, logs, metrics)
5. **Proposes remediations** with risk assessment
6. **Requires human approval** (safety-first)
7. **Documents everything** in detailed postmortems

## Architecture

```
Alert Event
    ↓
Triage Agent (classification)
    ↓
Hypothesis Agent (reasoning)
    ↓
Diagnostic Agent (tool-using)
    ↓
Remediation Planner (safe fixes)
    ↓
Human Approval (REQUIRED)
    ↓
Postmortem Writer
```

Built on **LangGraph** for:
- Deterministic workflows
- Stateful checkpoints
- Explicit guardrails
- Human-in-the-loop controls
- Full audit trails

## Quick Start

### Prerequisites

- Python 3.11+
- Kubernetes cluster access (kubeconfig)
- OpenAI API key
- Optional: Prometheus, Loki for full observability

### Installation

```bash
# Clone the repo
cd sre-autonomous-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cat > .env << EOF
OPENAI_API_KEY=sk-your-key-here
PROMETHEUS_URL=http://your-prometheus:9090
LOKI_URL=http://your-loki:3100
EOF
```

### Run Demo

```bash
# Run with example CrashLoopBackOff alert
python -m app.main examples/crashloop_alert.json
```

The agent will:
1. Classify the incident
2. Generate hypotheses
3. Run diagnostics (simulated if no cluster)
4. Propose remediation
5. Wait for approval
6. Generate postmortem

Check `postmortems/INC-*.md` for the full report.

### Launch Web UI 🎨

```bash
# Start the web interface
./run-ui.sh
```

Then open **http://localhost:8501** in your browser.

The UI provides:
- **Dashboard** - Real-time incident monitoring and metrics
- **Alert Submission** - Submit alerts manually, via templates, or JSON upload
- **Incidents** - View incident history and timeline
- **Postmortems** - Browse and download incident reports
- **Settings** - Configure environment and guardrails

Alternatively, run the API server:
```bash
# Start the REST API backend
./run-api.sh
```

API Documentation available at **http://localhost:8000/docs**

## Project Structure

```
sre-autonomous-agent/
├── app/
│   ├── graph/
│   │   ├── state.py          # LangGraph state definition
│   │   └── graph.py          # Workflow orchestration
│   │
│   ├── agents/
│   │   ├── triage.py         # Incident classification
│   │   ├── hypothesis.py     # Root cause reasoning
│   │   ├── diagnostics.py    # Evidence gathering
│   │   ├── remediation.py    # Fix planning
│   │   └── postmortem.py     # Documentation
│   │
│   ├── tools/
│   │   ├── kubernetes.py     # K8s API tools
│   │   ├── prometheus.py     # Metrics queries
│   │   └── logs.py           # Log analysis
│   │
│   ├── policies/
│   │   └── guardrails.yaml   # Safety policies
│   │
│   └── main.py               # Entry point
│
├── examples/
│   └── crashloop_alert.json  # Example alert
│
├── postmortems/              # Generated reports
├── requirements.txt
└── README.md
```

## Safety Guardrails

The agent enforces strict safety policies:

### Forbidden Actions
- Delete namespaces/services
- Modify RBAC/network policies
- Execute arbitrary commands
- Auto-apply without approval

### Namespace Access
- **Read/Write:** staging, dev, test
- **Read-only:** prod, production

### Human Approval Required
- Restart deployments
- Scale replicas
- Update configs
- Rollback deployments

See [app/policies/guardrails.yaml](app/policies/guardrails.yaml) for full policy.

## MVP Scope (Phase 1)

**Incident Type:** CrashLoopBackOff only

**Capabilities:**
- Diagnose pod crash causes
- Propose config/environment fixes
- Generate remediation PR
- Full postmortem documentation

**NOT Included:**
- Auto-execution (requires approval)
- Multiple incident types (coming in Phase 2)
- Slack integration (webhook placeholder ready)

## Configuration

### Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...

# Observability (optional)
PROMETHEUS_URL=http://prometheus:9090
LOKI_URL=http://loki:3100

# Kubernetes (auto-detected from kubeconfig)
# If running in-cluster, uses service account
```

### Guardrails

Edit `app/policies/guardrails.yaml` to customize:
- Allowed/forbidden actions
- Namespace permissions
- Risk thresholds
- Time windows for changes

## Human Approval Workflow

The agent **never** executes remediations without explicit human approval.

### CLI Approval

When the agent proposes a remediation, you'll see:

```
HUMAN APPROVAL REQUIRED
================================================================================
Approval ID: approval-abc123
Incident: CrashLoopBackOff
Root Cause: Missing DATABASE_URL environment variable

Proposed Remediation:
  Action: Add DATABASE_URL to deployment env
  Risk: low
  Requires PR: Yes

To approve, run:
  python -m app.cli.approve INC-20251229-a3f8b2e1
================================================================================
```

**Approve the remediation:**

```bash
python -m app.cli.approve INC-20251229-a3f8b2e1
```

**List pending approvals:**

```bash
python -m app.cli.approve --list
```

**Reject a remediation:**

```bash
python -m app.cli.approve --reject INC-20251229-a3f8b2e1 --reason "Too risky"
```

### Automated Execution

Once approved, the agent will:

1. **Execute** the remediation (patch deployment, add env vars, etc.)
2. **Verify** deployment health
3. **Rollback** automatically if verification fails
4. **Document** the outcome in the postmortem

### Rollback Protection

The executor saves deployment state before changes and automatically rolls back if:
- Deployment fails health check within 60 seconds
- New pods don't reach Ready state
- Remediation execution throws errors

Manual rollback is also available:

```python
from app.tools.remediation_executor import RemediationExecutor
executor = RemediationExecutor()
executor.rollback("INC-20251229-a3f8b2e1")
```

## Example Output

After running on the example alert:

```
Alert received: INC-20251229-a3f8b2e1
Alert: PodCrashLooping

Triage: CrashLoopBackOff (critical)
Hypotheses: 3 generated
Diagnostics: Root cause identified
Remediation: Config change (low risk)

HUMAN APPROVAL REQUIRED
Incident: CrashLoopBackOff
Root Cause: Missing DATABASE_URL environment variable
Proposed: Add DATABASE_URL to deployment env
Risk: low
Requires PR: Yes

[After approval]
✓ Remediation approved for incident INC-20251229-a3f8b2e1
Executing remediation...
Added DATABASE_URL environment variable
Waiting for deployment rollout...
Deployment my-app is healthy
✓ Successfully applied config change to my-app

Postmortem saved: postmortems/INC-20251229-a3f8b2e1.md
```

### Sample Postmortem

See generated markdown with:
- Complete timeline
- Root cause analysis
- Remediation plan
- Preventive measures
- Lessons learned

## Production Deployment

### Webhook Server (Coming)

```python
# Future: FastAPI webhook endpoint
@app.post("/alerts")
def receive_alert(alert: AlertPayload):
    return handle_alert_webhook(alert.dict())
```

### Slack Integration (Coming)

- Send remediation proposals to Slack
- Approval buttons
- Status updates
- Postmortem sharing

### Kubernetes Deployment

```yaml
# Deploy as K8s service
# ServiceAccount with read-only cluster access
# Optional: write access to staging namespaces
```

## Roadmap

### Phase 2: Multi-Incident
- OOMKilled
- ImagePullBackOff  
- NodeNotReady
- HighErrorRate

### Phase 3: Auto-Fix (with guardrails)
- Low-risk auto-remediation
- Blast radius control
- Automatic rollback on failure

### Phase 4: Learning
- Pattern recognition
- Custom playbooks
- Team-specific policies

## Contributing

This is a commercial product template. For production use:

1. Add real Slack integration
2. Implement proper JSON parsing (replace `eval()`)
3. Add comprehensive tests
4. Set up CI/CD
5. Harden security (secrets management)

## License

Proprietary - Commercial Use

---

## Why LangGraph?

We chose LangGraph over CrewAI because:

1. **Deterministic flows** - Critical for SRE reliability
2. **Stateful checkpoints** - Essential for HITL and recovery
3. **Explicit guardrails** - Production safety requirements
4. **Auditability** - Every decision is traceable

## Our Unfair Advantage

- **Kubernetes expertise** = instant credibility
- **Infra + AI** = very hard to replicate
- **Safety-first** = enterprise-ready from day one

## Next Steps

1. **Run the demo** with example alert
2. **Connect to your cluster** (update kubeconfig)
3. **Customize guardrails** for your environment
4. **Deploy webhook** for real alerts

---

**Built with LangGraph, Kubernetes, and AI that doesn't break production.**