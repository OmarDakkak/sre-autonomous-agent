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
- **Approvals** - Review and approve/reject remediation actions with one-click buttons
- **Postmortems** - Browse and download incident reports
- **Settings** - Configure environment and guardrails

Alternatively, run the API server:
```bash
# Start the REST API backend
./run-api.sh
```

API Documentation available at **http://localhost:8000/docs**

### Launch Webhook Server 🔔

Receive alerts from Prometheus Alertmanager, PagerDuty, and other monitoring systems:

```bash
# Start the webhook server
./run-webhook.sh
```

The webhook server will listen on **http://localhost:9000**

Configure Alertmanager to send alerts:

```yaml
# alertmanager.yml
receivers:
  - name: 'sre-agent'
    webhook_configs:
      - url: 'http://your-server:9000/webhook/alertmanager'
```

See [Webhook Server Guide](docs/WEBHOOK_SERVER.md) for full setup instructions.

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
│   │   ├── logs.py           # Log analysis
│   │   └── remediation_executor.py  # Execute approved fixes
│   │
│   ├── approval/
│   │   └── manager.py        # Approval state management
│   │
│   ├── integrations/
│   │   └── slack.py          # Slack notifications & approvals
│   │
│   ├── webhook/
│   │   └── server.py         # Alertmanager webhook receiver
│   │
│   ├── cli/
│   │   └── approve.py        # CLI approval commands
│   │
│   ├── policies/
│   │   └── guardrails.yaml   # Safety policies
│   │
│   └── main.py               # Entry point
│
├── ui/
│   ├── app.py                # Streamlit web interface
│   └── api.py                # FastAPI REST API
│
├── tests/
│   └── test_integration.py   # Real K8s integration tests
│
├── docs/
│   ├── APPROVAL_WORKFLOW.md  # Approval workflow guide
│   ├── SLACK_INTEGRATION.md  # Slack setup guide
│   └── WEBHOOK_SERVER.md     # Webhook server guide
│
├── examples/
│   └── crashloop_alert.json  # Example alert
│
├── postmortems/              # Generated reports
├── approvals/                # Approval requests
├── rollbacks/                # Pre-remediation snapshots
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

### Webhook Server

The webhook server receives alerts from Prometheus Alertmanager and other monitoring systems:

```bash
# Start webhook server
./run-webhook.sh

# Configure Alertmanager
cat > alertmanager.yml << EOF
receivers:
  - name: 'sre-agent'
    webhook_configs:
      - url: 'http://your-server:9000/webhook/alertmanager'
        send_resolved: false
EOF
```

Supported webhooks:
- **Alertmanager**: `POST /webhook/alertmanager`
- **PagerDuty**: `POST /webhook/pagerduty`
- **Generic**: `POST /webhook/alert`

See [Webhook Server Guide](docs/WEBHOOK_SERVER.md) for deployment instructions.

### Slack Integration

Send incident notifications and approval requests to Slack:

```bash
# Set environment variables
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
export SLACK_BOT_TOKEN="xoxb-your-bot-token"
export SLACK_CHANNEL="#sre-incidents"
```

The agent will:
- Send incident notifications to Slack
- Post approval requests with interactive buttons
- Update messages with execution results

See [Slack Integration Guide](docs/SLACK_INTEGRATION.md) for setup.

### Kubernetes Deployment

Deploy the agent as a Kubernetes service:

```yaml
# Deploy webhook server
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sre-agent-webhook
  namespace: monitoring
spec:
  replicas: 2
  selector:
    matchLabels:
      app: sre-agent-webhook
  template:
    metadata:
      labels:
        app: sre-agent-webhook
    spec:
      serviceAccountName: sre-agent
      containers:
      - name: webhook
        image: sre-agent-webhook:latest
        ports:
        - containerPort: 9000
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: sre-agent-secrets
              key: openai-api-key
---
apiVersion: v1
kind: Service
metadata:
  name: sre-agent-webhook
  namespace: monitoring
spec:
  selector:
    app: sre-agent-webhook
  ports:
  - port: 9000
    targetPort: 9000
```

Create RBAC permissions:

```yaml
# ServiceAccount with read/write access
apiVersion: v1
kind: ServiceAccount
metadata:
  name: sre-agent
  namespace: monitoring
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: sre-agent
rules:
- apiGroups: [""]
  resources: ["pods", "pods/log", "services", "events"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch", "patch", "update"]
```

See [Webhook Server Guide](docs/WEBHOOK_SERVER.md) for complete deployment instructions.

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

### Current Features ✅

- ✅ **LangGraph workflow** with checkpoints and HITL
- ✅ **5 specialized agents** (triage, hypothesis, diagnostics, remediation, postmortem)
- ✅ **Kubernetes tools** for pod diagnostics and remediation
- ✅ **Approval workflow** with CLI, UI, and API
- ✅ **Automated execution** with rollback on failure
- ✅ **Streamlit web UI** with approval buttons
- ✅ **FastAPI REST API** with approval endpoints
- ✅ **Slack integration** with interactive approval buttons
- ✅ **Webhook server** for Alertmanager, PagerDuty, and custom alerts
- ✅ **Real integration tests** with actual Kubernetes

### Production Readiness Checklist

For production deployment, complete these improvements:

1. **Code Quality**
   - [ ] Replace `eval()` with proper JSON parsing
   - [ ] Add comprehensive error handling
   - [ ] Implement structured logging

2. **Testing**
   - [x] Integration tests with real Kubernetes
   - [ ] Unit tests for all agents
   - [ ] Load testing for webhook server

3. **Security**
   - [ ] Secrets management (HashiCorp Vault)
   - [ ] Webhook signature validation
   - [ ] Rate limiting on API endpoints

4. **Observability**
   - [ ] Prometheus metrics endpoint
   - [ ] Distributed tracing (Jaeger)
   - [ ] Structured logging with correlation IDs

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