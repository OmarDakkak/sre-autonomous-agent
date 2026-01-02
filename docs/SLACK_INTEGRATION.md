# Slack Integration Guide

This guide shows you how to integrate the SRE Autonomous Agent with Slack for incident notifications and approval workflows.

## Features

- 🚨 **Incident Notifications** - Real-time alerts when incidents are detected
- ⚠️ **Approval Requests** - Interactive buttons to approve/reject remediations
- ✅ **Execution Results** - Status updates after remediation execution
- 🔘 **Interactive Buttons** - One-click approval/rejection from Slack

## Setup

### 1. Create a Slack App

1. Go to https://api.slack.com/apps
2. Click **Create New App** → **From scratch**
3. Name your app (e.g., "SRE Autonomous Agent")
4. Select your workspace
5. Click **Create App**

### 2. Enable Incoming Webhooks

For basic notifications:

1. In your app settings, go to **Incoming Webhooks**
2. Toggle **Activate Incoming Webhooks** to On
3. Click **Add New Webhook to Workspace**
4. Select the channel (e.g., `#sre-incidents`)
5. Copy the webhook URL

Set the webhook URL in your environment:

```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

### 3. Enable Interactive Components (Optional)

For approval buttons:

1. Go to **Interactivity & Shortcuts**
2. Toggle **Interactivity** to On
3. Set **Request URL** to your webhook endpoint:
   ```
   https://your-domain.com/slack/interactions
   ```
4. Click **Save Changes**

### 4. Add Bot Token Scopes

1. Go to **OAuth & Permissions**
2. Under **Bot Token Scopes**, add:
   - `chat:write` - Post messages
   - `chat:write.public` - Post to public channels
   - `channels:read` - List channels
   - `users:read` - Get user info

3. Click **Install to Workspace**
4. Copy the **Bot User OAuth Token**

Set the bot token in your environment:

```bash
export SLACK_BOT_TOKEN="xoxb-your-bot-token"
export SLACK_CHANNEL="#sre-incidents"
```

### 5. Update Environment Variables

Add to your `.env` file:

```bash
# Slack Integration
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_CHANNEL=#sre-incidents
```

## Usage

### Send Incident Notification

```python
from app.integrations.slack import notify_incident

# Send incident notification
notify_incident(
    incident_id="INC-20260102-abc123",
    incident_type="CrashLoopBackOff",
    severity="critical",
    root_cause="Missing DATABASE_URL environment variable"
)
```

### Send Approval Request

```python
from app.integrations.slack import send_approval_to_slack

# Send approval request with interactive buttons
send_approval_to_slack(
    incident_id="INC-20260102-abc123",
    root_cause="Missing DATABASE_URL environment variable",
    remediation_action="Add DATABASE_URL to deployment env",
    risk_level="low",
    remediation_plan={
        "description": "Add DATABASE_URL environment variable",
        "action_type": "config_change",
        "risk_level": "low"
    }
)
```

### Manual Integration in Graph

Update [app/graph/graph.py](app/graph/graph.py) to send Slack notifications:

```python
from app.integrations.slack import notify_incident, send_approval_to_slack

def human_approval_node(state: IncidentState) -> IncidentState:
    """Human-in-the-loop checkpoint with Slack integration"""
    
    # ... existing approval code ...
    
    # Send to Slack
    send_approval_to_slack(
        incident_id=state["incident_id"],
        root_cause=state["root_cause"],
        remediation_action=state["remediation_plan"]["description"],
        risk_level=state["remediation_plan"]["risk_level"],
        remediation_plan=state["remediation_plan"]
    )
    
    return state
```

## Interactive Approval Buttons

### Setup Interaction Endpoint

Create a FastAPI endpoint to handle Slack interactions:

```python
from fastapi import FastAPI, Request
from app.integrations.slack import SlackIntegration

app = FastAPI()
slack = SlackIntegration()

@app.post("/slack/interactions")
async def handle_slack_interaction(request: Request):
    """Handle Slack button clicks"""
    
    # Parse Slack payload
    form_data = await request.form()
    payload = json.loads(form_data["payload"])
    
    # Handle the action
    response = slack.handle_approval_action(payload)
    
    return response
```

### Slack Message Format

The approval request will look like this in Slack:

```
⚠️ Remediation Approval Required

Incident ID: INC-20260102-abc123
Risk Level: 🟢 LOW

Root Cause:
Missing DATABASE_URL environment variable

Proposed Action:
Add DATABASE_URL to deployment env

[✓ Approve] [✗ Reject] [View Details]
```

When a user clicks **Approve**, the agent will:
1. Mark the approval as approved
2. Execute the remediation
3. Update the message with the result

## Testing

### Test Webhook Notification

```bash
# Send a test notification
python -c "
from app.integrations.slack import notify_incident
notify_incident(
    'TEST-123',
    'CrashLoopBackOff',
    'critical',
    'Test notification'
)
"
```

You should see a message in your Slack channel.

### Test Approval Request

```bash
# Send a test approval request
python -c "
from app.integrations.slack import send_approval_to_slack
send_approval_to_slack(
    'TEST-123',
    'Test root cause',
    'Test remediation action',
    'low',
    {'description': 'Test', 'action_type': 'config_change'}
)
"
```

## Troubleshooting

### Webhook not working

1. Check that `SLACK_WEBHOOK_URL` is set correctly
2. Verify the webhook URL in Slack app settings
3. Test with curl:
   ```bash
   curl -X POST -H 'Content-type: application/json' \
     --data '{"text":"Test message"}' \
     $SLACK_WEBHOOK_URL
   ```

### Bot token not working

1. Ensure bot is installed to workspace
2. Verify bot has correct scopes
3. Check that bot is invited to the target channel:
   ```
   /invite @YourBotName
   ```

### Interactive buttons not responding

1. Verify **Interactivity** is enabled
2. Check **Request URL** is publicly accessible
3. Ensure endpoint returns proper JSON response
4. Check Slack app logs for errors

## Security Best Practices

1. **Never commit tokens** - Use environment variables
2. **Verify Slack signatures** - Validate incoming webhook requests
3. **Use HTTPS** - For interaction endpoints
4. **Rotate tokens** - Regularly update bot tokens
5. **Limit scopes** - Only grant necessary permissions

## Example: Full Integration

```python
# In your graph.py
from app.integrations.slack import SlackIntegration

slack = SlackIntegration()

def triage_agent(state: IncidentState) -> IncidentState:
    # ... existing triage code ...
    
    # Notify Slack
    slack.send_incident_notification(
        state["incident_id"],
        state["incident_type"],
        state.get("severity", "warning")
    )
    
    return state

def human_approval_node(state: IncidentState) -> IncidentState:
    # ... existing approval code ...
    
    # Send approval request to Slack
    slack.send_approval_request(
        state["incident_id"],
        state["root_cause"],
        state["remediation_plan"]["description"],
        state["remediation_plan"]["risk_level"],
        state["remediation_plan"]
    )
    
    return state
```

## Advanced: Custom Message Formatting

Customize Slack messages by extending the `SlackIntegration` class:

```python
from app.integrations.slack import SlackIntegration

class CustomSlackIntegration(SlackIntegration):
    def send_approval_request(self, incident_id, root_cause, remediation_action, risk_level, remediation_plan):
        # Custom message format
        message = {
            "blocks": [
                # Your custom blocks
            ]
        }
        # Send custom message
        return self._send_slack_message(message)
```

## Resources

- [Slack API Documentation](https://api.slack.com/)
- [Block Kit Builder](https://app.slack.com/block-kit-builder) - Design interactive messages
- [Slack SDK for Python](https://slack.dev/python-slack-sdk/)
