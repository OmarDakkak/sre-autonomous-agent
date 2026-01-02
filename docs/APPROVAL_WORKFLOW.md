# Automated Remediation Workflow Guide

This guide demonstrates the complete human-in-the-loop approval and automated remediation workflow.

## Overview

The workflow consists of:

1. **Incident Detection** - Agent analyzes alert and proposes remediation
2. **Human Approval** - SRE reviews and approves/rejects via CLI
3. **Automated Execution** - Agent applies approved changes to Kubernetes
4. **Health Verification** - Agent verifies deployment health
5. **Auto-Rollback** - Automatic rollback if verification fails

## Testing the Workflow

### 1. Run Integration Tests

The integration tests create a real Kubernetes deployment and test the entire flow:

```bash
# Ensure you have kubectl access to a test cluster
kubectl config current-context

# Run the integration tests
python -m pytest tests/test_integration.py -v
```

The test will:
- Create a test namespace
- Deploy an app with missing DATABASE_URL (causes crash)
- Wait for CrashLoopBackOff
- Run the agent to diagnose and propose fix
- Test the approval and execution flow

### 2. Manual Workflow Test

#### Step 1: Submit an alert

```bash
# Create a test alert (or use the example)
python -m app.main examples/crashloop_alert.json
```

You'll see output like:
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

#### Step 2: Review pending approvals

```bash
python -m app.cli.approve --list
```

Output:
```
PENDING APPROVALS (1)
================================================================================

Incident ID: INC-20251229-a3f8b2e1
  Root Cause: Missing DATABASE_URL environment variable
  Action: Add DATABASE_URL to deployment env
  Risk: low
  Created: 2025-12-31T10:30:45Z
  Approval ID: approval-abc123

================================================================================
To approve: python -m app.cli.approve <incident_id>
To reject: python -m app.cli.approve --reject <incident_id>
```

#### Step 3: Approve the remediation

```bash
python -m app.cli.approve INC-20251229-a3f8b2e1
```

You'll be prompted:
```
REMEDIATION APPROVAL
================================================================================
Incident ID: INC-20251229-a3f8b2e1
Root Cause: Missing DATABASE_URL environment variable
Action: Add DATABASE_URL to deployment env
Risk Level: low
Created: 2025-12-31T10:30:45Z

================================================================================

Approve this remediation? [y/N]: y

✓ Remediation approved for incident INC-20251229-a3f8b2e1

Executing remediation...
================================================================================
EXECUTING REMEDIATION: INC-20251229-a3f8b2e1
================================================================================
Action: Add DATABASE_URL to deployment env
Namespace: default
Risk Level: low
Applying config change to deployment: my-app
Saved rollback data to rollbacks/INC-20251229-a3f8b2e1.json
Added DATABASE_URL environment variable
Waiting for deployment rollout...
Deployment my-app is healthy

✓ Successfully applied config change to my-app
```

#### Step 4: Verify the fix

```bash
# Check the deployment
kubectl get deployment my-app -o yaml | grep -A5 env:

# Check pod status
kubectl get pods -l app=my-app

# Check postmortem
cat postmortems/INC-20251229-a3f8b2e1.md
```

### 3. Test Rejection Flow

```bash
# Reject instead of approving
python -m app.cli.approve --reject INC-20251229-a3f8b2e1 --reason "Need more investigation"
```

Output:
```
REMEDIATION REJECTION
================================================================================
Incident ID: INC-20251229-a3f8b2e1
Root Cause: Missing DATABASE_URL environment variable
Action: Add DATABASE_URL to deployment env

================================================================================

✓ Remediation rejected for incident INC-20251229-a3f8b2e1
```

### 4. Test Rollback

If a remediation fails health checks, it will automatically roll back:

```python
# Simulate a bad remediation
from app.tools.remediation_executor import RemediationExecutor
from app.approval import get_approval_manager

executor = RemediationExecutor()
approval_manager = get_approval_manager()

# Manual rollback if needed
success, message = executor.rollback("INC-20251229-a3f8b2e1")
print(f"Rollback: {success} - {message}")
```

## Approval State Files

Approval requests are stored in `approvals/` directory:

```bash
# View approval state
cat approvals/INC-20251229-a3f8b2e1.json
```

Example:
```json
{
  "approval_id": "approval-abc123",
  "incident_id": "INC-20251229-a3f8b2e1",
  "root_cause": "Missing DATABASE_URL environment variable",
  "remediation_action": "Add DATABASE_URL to deployment env",
  "risk_level": "low",
  "status": "approved",
  "created_at": "2025-12-31T10:30:45Z",
  "approved_at": "2025-12-31T10:35:12Z",
  "approved_by": "cli-user",
  "comment": "Reviewed and approved"
}
```

## Rollback State Files

Pre-remediation snapshots are stored in `rollbacks/` directory:

```bash
# View rollback data
cat rollbacks/INC-20251229-a3f8b2e1.json
```

This contains the full deployment spec before changes, enabling safe rollback.

## CLI Commands Reference

### List Pending Approvals
```bash
python -m app.cli.approve --list
```

### Approve a Remediation
```bash
# Basic approval
python -m app.cli.approve INC-20251229-a3f8b2e1

# With comment
python -m app.cli.approve INC-20251229-a3f8b2e1 --comment "Approved after review"
```

### Reject a Remediation
```bash
# Basic rejection
python -m app.cli.approve --reject INC-20251229-a3f8b2e1

# With reason
python -m app.cli.approve --reject INC-20251229-a3f8b2e1 --reason "Too risky"
```

## Supported Remediation Types

The RemediationExecutor currently supports:

1. **Config Changes** - Add/update environment variables
2. **Restart Deployment** - Rolling restart via annotation
3. **Scale Deployment** - Adjust replica count
4. **Rollback Deployment** - Rollback to previous version

Each remediation type includes:
- Pre-change snapshot for rollback
- Health verification (60s timeout)
- Automatic rollback on failure

## Safety Features

### 1. Pre-execution Validation
- Verifies deployment exists
- Checks namespace access
- Validates action type

### 2. Health Checks
After applying changes, the executor:
- Waits up to 60 seconds for rollout
- Verifies `ready_replicas == desired_replicas`
- Monitors pod status

### 3. Automatic Rollback
If health checks fail:
- Restores deployment from snapshot
- Logs failure reason
- Updates incident with failure status

### 4. Audit Trail
All actions are logged:
- Approval requests in `approvals/`
- Rollback snapshots in `rollbacks/`
- Execution results in postmortems

## Next Steps

1. **Add UI Approval** - Buttons in Streamlit dashboard
2. **Add API Endpoint** - `POST /api/approve/{incident_id}`
3. **Slack Integration** - Approval buttons in Slack
4. **Webhook Server** - Receive alerts from Alertmanager
5. **Production Deployment** - K8s ServiceAccount with RBAC

## Troubleshooting

### Permission Denied
```
Error: Kubernetes API error: Forbidden
```
**Solution:** Ensure your kubeconfig has write access to the target namespace.

### No Pending Approval Found
```
Error: No pending approval found for incident INC-xyz
```
**Solution:** Check `approvals/` directory or run `--list` to see all pending approvals.

### Rollback Failed
```
Error: No rollback data found
```
**Solution:** Rollback data is only saved when executor creates a snapshot before changes. If no snapshot exists, manual recovery is needed.

## Architecture

```
Alert → Graph → Remediation Agent → Approval Node
                                          ↓
                                    [PAUSE]
                                          ↓
                CLI Approval ← Human Review
                      ↓
                Remediation Executor
                      ↓
                Health Check → OK → Postmortem
                      ↓
                   FAILED
                      ↓
                Auto Rollback → Postmortem
```

The workflow is fully auditable with checkpoints at every stage.
