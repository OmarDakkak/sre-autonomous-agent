# API Reference

Complete REST API documentation for the SRE Autonomous Agent.

## Base URLs

- **REST API**: `http://localhost:8000`
- **Webhook Server**: `http://localhost:9000`
- **Streamlit UI**: `http://localhost:8501`

## REST API Endpoints

### Health & Status

#### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-02T10:30:00Z"
}
```

#### GET /

Service information.

**Response:**
```json
{
  "service": "SRE Autonomous Agent API",
  "version": "1.0.0",
  "status": "running"
}
```

### Alerts

#### POST /api/alerts

Submit a new alert for processing.

**Request Body:**
```json
{
  "status": "firing",
  "commonLabels": {
    "alertname": "PodCrashLooping",
    "severity": "critical",
    "namespace": "default",
    "pod": "my-app-xyz"
  },
  "commonAnnotations": {
    "summary": "Pod is crash looping",
    "description": "Pod has restarted 5 times"
  },
  "startsAt": "2026-01-02T10:30:00Z"
}
```

**Response:**
```json
{
  "incident_id": "INC-20260102-abc123",
  "status": "processing",
  "message": "Alert received. Incident INC-20260102-abc123 is being processed."
}
```

#### GET /api/alerts/examples

Get example alert templates.

**Response:**
```json
[
  {
    "name": "crashloop_alert",
    "template": {
      "status": "firing",
      "commonLabels": {...},
      "commonAnnotations": {...}
    }
  }
]
```

### Incidents

#### GET /api/incidents

List all processed incidents.

**Response:**
```json
[
  {
    "incident_id": "INC-20260102-abc123",
    "timestamp": "2026-01-02T10:30:00Z",
    "postmortem": "# Incident Postmortem\n..."
  }
]
```

#### GET /api/incidents/{incident_id}

Get specific incident details.

**Response:**
```json
{
  "incident_id": "INC-20260102-abc123",
  "timestamp": "2026-01-02T10:30:00Z",
  "postmortem": "# Incident Postmortem\n..."
}
```

### Approvals

#### GET /api/approvals

List approval requests.

**Query Parameters:**
- `status` (optional): Filter by status (`pending`, `approved`, `rejected`)

**Examples:**
```bash
# Get all pending approvals
GET /api/approvals?status=pending

# Get all approvals (any status)
GET /api/approvals
```

**Response:**
```json
[
  {
    "approval_id": "approval-xyz789",
    "incident_id": "INC-20260102-abc123",
    "root_cause": "Missing DATABASE_URL environment variable",
    "remediation_action": "Add DATABASE_URL to deployment env",
    "risk_level": "low",
    "status": "pending",
    "created_at": "2026-01-02T10:30:00Z"
  }
]
```

#### GET /api/approvals/{incident_id}

Get approval request for a specific incident.

**Response:**
```json
{
  "approval_id": "approval-xyz789",
  "incident_id": "INC-20260102-abc123",
  "root_cause": "Missing DATABASE_URL environment variable",
  "remediation_action": "Add DATABASE_URL to deployment env",
  "risk_level": "low",
  "status": "pending",
  "created_at": "2026-01-02T10:30:00Z",
  "remediation_plan": {
    "description": "Add DATABASE_URL environment variable",
    "action_type": "config_change",
    "risk_level": "low"
  }
}
```

#### POST /api/approvals/{incident_id}/approve

Approve a remediation action.

**Request Body:**
```json
{
  "approved_by": "api-user",
  "comment": "Reviewed and approved"
}
```

**Response:**
```json
{
  "incident_id": "INC-20260102-abc123",
  "status": "approved",
  "execution_success": true,
  "execution_message": "Successfully applied config change to my-app",
  "approved_by": "api-user",
  "approved_at": "2026-01-02T10:35:00Z"
}
```

#### POST /api/approvals/{incident_id}/reject

Reject a remediation action.

**Request Body:**
```json
{
  "approved_by": "api-user",
  "reason": "Too risky for production"
}
```

**Response:**
```json
{
  "incident_id": "INC-20260102-abc123",
  "status": "rejected",
  "rejected_by": "api-user",
  "rejected_at": "2026-01-02T10:35:00Z",
  "reason": "Too risky for production"
}
```

### Statistics

#### GET /api/stats

Get system statistics.

**Response:**
```json
{
  "total_incidents": 42,
  "incidents_today": 3,
  "active_incidents": 1
}
```

## Webhook Endpoints

### Alertmanager Webhook

#### POST /webhook/alertmanager

Receive alerts from Prometheus Alertmanager.

**Request Body:**
```json
{
  "version": "4",
  "groupKey": "test",
  "status": "firing",
  "receiver": "sre-agent",
  "groupLabels": {},
  "commonLabels": {
    "alertname": "PodCrashLooping",
    "severity": "critical",
    "namespace": "default",
    "pod": "my-app-xyz"
  },
  "commonAnnotations": {
    "summary": "Pod is crash looping"
  },
  "externalURL": "http://alertmanager:9093",
  "alerts": [
    {
      "status": "firing",
      "labels": {...},
      "annotations": {...},
      "startsAt": "2026-01-02T10:30:00Z"
    }
  ]
}
```

**Response:**
```json
{
  "message": "Processing 1 alerts",
  "incident_ids": ["INC-20260102-abc123"],
  "status": "processing"
}
```

### PagerDuty Webhook

#### POST /webhook/pagerduty

Receive webhooks from PagerDuty.

**Request Body:**
```json
{
  "messages": [
    {
      "event": "incident.trigger",
      "incident": {
        "incident_key": "srv01/HTTP",
        "title": "Production API Down",
        "urgency": "high",
        "html_url": "https://acme.pagerduty.com/incidents/ABC123"
      }
    }
  ]
}
```

**Response:**
```json
{
  "message": "Processing 1 incidents",
  "incident_ids": ["INC-20260102-abc123"],
  "status": "processing"
}
```

### Generic Webhook

#### POST /webhook/alert

Receive generic alerts.

**Request Body:**
```json
{
  "status": "firing",
  "commonLabels": {
    "alertname": "CustomAlert",
    "severity": "critical"
  },
  "commonAnnotations": {
    "summary": "Brief description"
  }
}
```

**Response:**
```json
{
  "message": "Alert received and processing",
  "incident_id": "INC-20260102-abc123",
  "status": "processing"
}
```

## CLI Commands

### Approval Management

#### List Pending Approvals

```bash
python -m app.cli.approve --list
```

#### Approve Remediation

```bash
# Basic approval
python -m app.cli.approve INC-20260102-abc123

# With comment
python -m app.cli.approve INC-20260102-abc123 --comment "Approved after review"
```

#### Reject Remediation

```bash
# Basic rejection
python -m app.cli.approve --reject INC-20260102-abc123

# With reason
python -m app.cli.approve --reject INC-20260102-abc123 --reason "Too risky"
```

## Error Responses

All endpoints return standard error responses:

### 400 Bad Request

```json
{
  "detail": "Rejection reason is required"
}
```

### 404 Not Found

```json
{
  "detail": "Incident not found"
}
```

### 500 Internal Server Error

```json
{
  "detail": "Error processing incident: <error message>"
}
```

## Authentication (Coming Soon)

Future versions will support API key authentication:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8000/api/incidents
```

## Rate Limiting (Coming Soon)

API rate limits will be implemented:

- **100 requests/minute** per IP
- **1000 requests/hour** per API key

## Examples

### Submit Alert via API

```bash
curl -X POST http://localhost:8000/api/alerts \
  -H 'Content-Type: application/json' \
  -d '{
    "status": "firing",
    "commonLabels": {
      "alertname": "PodCrashLooping",
      "severity": "critical",
      "namespace": "default",
      "pod": "my-app-xyz"
    },
    "commonAnnotations": {
      "summary": "Pod is crash looping"
    }
  }'
```

### List Pending Approvals

```bash
curl http://localhost:8000/api/approvals?status=pending
```

### Approve Remediation

```bash
curl -X POST http://localhost:8000/api/approvals/INC-20260102-abc123/approve \
  -H 'Content-Type: application/json' \
  -d '{
    "approved_by": "john.doe",
    "comment": "Reviewed and looks good"
  }'
```

### Get Incident Details

```bash
curl http://localhost:8000/api/incidents/INC-20260102-abc123
```

## Interactive API Documentation

Access the auto-generated Swagger UI documentation:

**http://localhost:8000/docs**

Features:
- Try out endpoints directly in the browser
- View request/response schemas
- See example payloads
- Test authentication (when implemented)

## SDK Examples

### Python

```python
import requests

# Submit alert
response = requests.post(
    "http://localhost:8000/api/alerts",
    json={
        "status": "firing",
        "commonLabels": {
            "alertname": "PodCrashLooping",
            "severity": "critical"
        },
        "commonAnnotations": {
            "summary": "Pod is crash looping"
        }
    }
)

incident_id = response.json()["incident_id"]
print(f"Created incident: {incident_id}")

# List pending approvals
response = requests.get("http://localhost:8000/api/approvals?status=pending")
approvals = response.json()

for approval in approvals:
    print(f"Pending: {approval['incident_id']}")
    
    # Approve
    requests.post(
        f"http://localhost:8000/api/approvals/{approval['incident_id']}/approve",
        json={"approved_by": "automation", "comment": "Auto-approved"}
    )
```

### JavaScript

```javascript
// Submit alert
const response = await fetch('http://localhost:8000/api/alerts', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    status: 'firing',
    commonLabels: {
      alertname: 'PodCrashLooping',
      severity: 'critical'
    },
    commonAnnotations: {
      summary: 'Pod is crash looping'
    }
  })
});

const data = await response.json();
console.log(`Created incident: ${data.incident_id}`);

// List pending approvals
const approvalsResponse = await fetch('http://localhost:8000/api/approvals?status=pending');
const approvals = await approvalsResponse.json();

for (const approval of approvals) {
  console.log(`Pending: ${approval.incident_id}`);
  
  // Approve
  await fetch(`http://localhost:8000/api/approvals/${approval.incident_id}/approve`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      approved_by: 'automation',
      comment: 'Auto-approved'
    })
  });
}
```

## Webhooks Best Practices

1. **Idempotency** - Webhook endpoints are idempotent; duplicate alerts won't create duplicate incidents
2. **Async Processing** - Alerts are processed in background tasks
3. **Timeout** - Webhook requests should complete within 10 seconds
4. **Retry Logic** - Implement retry with exponential backoff
5. **Validation** - Validate webhook signatures (when authentication is added)

## Support

For questions or issues:
- Check the [Webhook Server Guide](docs/WEBHOOK_SERVER.md)
- Check the [Slack Integration Guide](docs/SLACK_INTEGRATION.md)
- Check the [Approval Workflow Guide](docs/APPROVAL_WORKFLOW.md)
