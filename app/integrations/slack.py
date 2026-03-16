"""
Slack Integration for SRE Autonomous Agent

Sends incident notifications and approval requests to Slack with interactive buttons.
Handles approval/rejection actions via Slack Interactivity.
"""

import os
import json
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import requests
from pathlib import Path

from app.approval import get_approval_manager
from app.tools.remediation_executor import RemediationExecutor


class SlackIntegration:
    """Slack integration for incident notifications and approvals"""
    
    def __init__(self, webhook_url: Optional[str] = None, bot_token: Optional[str] = None):
        """
        Initialize Slack integration
        
        Args:
            webhook_url: Slack incoming webhook URL for notifications
            bot_token: Slack bot token for interactive features
        """
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
        self.bot_token = bot_token or os.getenv("SLACK_BOT_TOKEN")
        
        if not self.webhook_url:
            print("Warning: SLACK_WEBHOOK_URL not configured")
        
        if not self.bot_token:
            print("Warning: SLACK_BOT_TOKEN not configured for interactive features")
    
    def send_incident_notification(
        self,
        incident_id: str,
        incident_type: str,
        severity: str,
        root_cause: Optional[str] = None
    ) -> bool:
        """
        Send incident notification to Slack
        
        Args:
            incident_id: Unique incident identifier
            incident_type: Type of incident (e.g., CrashLoopBackOff)
            severity: Severity level (critical, warning, info)
            root_cause: Identified root cause (optional)
        
        Returns:
            bool: True if sent successfully
        """
        if not self.webhook_url:
            print("Slack webhook not configured")
            return False
        
        # Severity color mapping
        colors = {
            "critical": "#dc3545",
            "warning": "#ffc107",
            "info": "#17a2b8"
        }
        
        # Build message
        message = {
            "text": f"🚨 New Incident: {incident_id}",
            "attachments": [{
                "color": colors.get(severity.lower(), "#6c757d"),
                "fields": [
                    {
                        "title": "Incident ID",
                        "value": incident_id,
                        "short": True
                    },
                    {
                        "title": "Type",
                        "value": incident_type,
                        "short": True
                    },
                    {
                        "title": "Severity",
                        "value": severity.upper(),
                        "short": True
                    }
                ],
                "footer": "SRE Autonomous Agent",
                "ts": int(datetime.now(timezone.utc).timestamp())
            }]
        }
        
        if root_cause:
            message["attachments"][0]["fields"].append({
                "title": "Root Cause",
                "value": root_cause,
                "short": False
            })
        
        try:
            response = requests.post(
                self.webhook_url,
                json=message,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            return response.status_code == 200
        
        except Exception as e:
            print(f"Error sending Slack notification: {e}")
            return False
    
    def send_approval_request(
        self,
        incident_id: str,
        root_cause: str,
        remediation_action: str,
        risk_level: str,
        remediation_plan: Dict[str, Any],
        channel: Optional[str] = None
    ) -> bool:
        """
        Send approval request to Slack with interactive buttons
        
        Args:
            incident_id: Unique incident identifier
            root_cause: Identified root cause
            remediation_action: Proposed remediation
            risk_level: Risk level (low, medium, high)
            remediation_plan: Full remediation plan dict
            channel: Slack channel to post to (default: from env)
        
        Returns:
            bool: True if sent successfully
        """
        if not self.bot_token:
            print("Slack bot token not configured. Using webhook fallback.")
            return self._send_approval_request_webhook(
                incident_id, root_cause, remediation_action, risk_level
            )
        
        channel = channel or os.getenv("SLACK_CHANNEL", "#sre-incidents")
        
        # Risk level emoji
        risk_emoji = {
            "low": "🟢",
            "medium": "🟡",
            "high": "🔴"
        }
        
        # Build interactive message
        message = {
            "channel": channel,
            "text": f"⚠️ Approval Required: {incident_id}",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "⚠️ Remediation Approval Required"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Incident ID:*\n{incident_id}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Risk Level:*\n{risk_emoji.get(risk_level, '⚪')} {risk_level.upper()}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Root Cause:*\n{root_cause}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Proposed Action:*\n{remediation_action}"
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "actions",
                    "block_id": f"approval_{incident_id}",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "✓ Approve"
                            },
                            "style": "primary",
                            "action_id": "approve_remediation",
                            "value": json.dumps({
                                "incident_id": incident_id,
                                "action": "approve"
                            })
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "✗ Reject"
                            },
                            "style": "danger",
                            "action_id": "reject_remediation",
                            "value": json.dumps({
                                "incident_id": incident_id,
                                "action": "reject"
                            })
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "View Details"
                            },
                            "action_id": "view_details",
                            "value": incident_id
                        }
                    ]
                }
            ]
        }
        
        try:
            response = requests.post(
                "https://slack.com/api/chat.postMessage",
                json=message,
                headers={
                    "Authorization": f"Bearer {self.bot_token}",
                    "Content-Type": "application/json"
                },
                timeout=10
            )
            
            result = response.json()
            
            if not result.get("ok"):
                print(f"Slack API error: {result.get('error')}")
                return False
            
            return True
        
        except Exception as e:
            print(f"Error sending Slack approval request: {e}")
            return False
    
    def _send_approval_request_webhook(
        self,
        incident_id: str,
        root_cause: str,
        remediation_action: str,
        risk_level: str
    ) -> bool:
        """Fallback: Send approval request via webhook (no interactive buttons)"""
        if not self.webhook_url:
            return False
        
        message = {
            "text": f"⚠️ Approval Required: {incident_id}",
            "attachments": [{
                "color": "#ffc107",
                "fields": [
                    {
                        "title": "Incident ID",
                        "value": incident_id,
                        "short": True
                    },
                    {
                        "title": "Risk Level",
                        "value": risk_level.upper(),
                        "short": True
                    },
                    {
                        "title": "Root Cause",
                        "value": root_cause,
                        "short": False
                    },
                    {
                        "title": "Proposed Action",
                        "value": remediation_action,
                        "short": False
                    }
                ],
                "footer": "Use CLI to approve: python -m app.cli.approve " + incident_id
            }]
        }
        
        try:
            response = requests.post(
                self.webhook_url,
                json=message,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            return response.status_code == 200
        
        except Exception as e:
            print(f"Error sending webhook: {e}")
            return False
    
    def handle_approval_action(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle Slack interactive button action
        
        This should be called from your Slack interaction webhook endpoint.
        
        Args:
            payload: Slack interaction payload
        
        Returns:
            dict: Response to send back to Slack
        """
        try:
            # Extract action info
            actions = payload.get("actions", [])
            if not actions:
                return {"text": "No action found"}
            
            action = actions[0]
            action_id = action.get("action_id")
            value = json.loads(action.get("value", "{}"))
            incident_id = value.get("incident_id")
            
            user = payload.get("user", {})
            username = user.get("username", "slack-user")
            
            approval_manager = get_approval_manager()
            executor = RemediationExecutor()
            
            if action_id == "approve_remediation":
                # Get approval request
                pending = approval_manager.list_pending()
                request = next((r for r in pending if r.incident_id == incident_id), None)
                
                if not request:
                    return {
                        "text": f"❌ No pending approval found for {incident_id}"
                    }
                
                # Approve
                approval_manager.approve(incident_id, username, "Approved via Slack")
                
                # Execute remediation
                success, message = executor.execute_remediation(
                    incident_id,
                    request.remediation_plan,
                    request.alert_data
                )
                
                if success:
                    return {
                        "text": f"✅ Remediation approved and executed successfully!\n\n{message}",
                        "replace_original": True
                    }
                else:
                    return {
                        "text": f"⚠️ Remediation approved but execution failed:\n\n{message}",
                        "replace_original": True
                    }
            
            elif action_id == "reject_remediation":
                # Reject
                approval_manager.reject(
                    incident_id,
                    username,
                    "Rejected via Slack"
                )
                
                return {
                    "text": f"❌ Remediation rejected by {username}",
                    "replace_original": True
                }
            
            elif action_id == "view_details":
                # Return details
                approval_file = Path("approvals") / f"{incident_id}.json"
                if approval_file.exists():
                    with open(approval_file) as f:
                        approval_data = json.load(f)
                    
                    return {
                        "text": f"Incident Details for {incident_id}",
                        "blocks": [
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"```{json.dumps(approval_data, indent=2)}```"
                                }
                            }
                        ]
                    }
                else:
                    return {"text": "Details not found"}
            
            return {"text": "Unknown action"}
        
        except Exception as e:
            return {"text": f"Error processing action: {str(e)}"}
    
    def send_execution_result(
        self,
        incident_id: str,
        success: bool,
        message: str,
        channel: Optional[str] = None
    ) -> bool:
        """
        Send execution result notification
        
        Args:
            incident_id: Unique incident identifier
            success: Whether execution was successful
            message: Execution result message
            channel: Slack channel (optional)
        
        Returns:
            bool: True if sent successfully
        """
        if not self.webhook_url:
            return False
        
        emoji = "✅" if success else "❌"
        color = "#28a745" if success else "#dc3545"
        
        slack_message = {
            "text": f"{emoji} Remediation Result: {incident_id}",
            "attachments": [{
                "color": color,
                "fields": [
                    {
                        "title": "Incident ID",
                        "value": incident_id,
                        "short": True
                    },
                    {
                        "title": "Status",
                        "value": "Success" if success else "Failed",
                        "short": True
                    },
                    {
                        "title": "Message",
                        "value": message,
                        "short": False
                    }
                ],
                "footer": "SRE Autonomous Agent",
                "ts": int(datetime.now(timezone.utc).timestamp())
            }]
        }
        
        try:
            response = requests.post(
                self.webhook_url,
                json=slack_message,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            return response.status_code == 200
        
        except Exception as e:
            print(f"Error sending execution result: {e}")
            return False


def send_approval_to_slack(
    incident_id: str,
    root_cause: str,
    remediation_action: str,
    risk_level: str,
    remediation_plan: Dict[str, Any]
) -> bool:
    """
    Convenience function to send approval request to Slack
    """
    slack = SlackIntegration()
    return slack.send_approval_request(
        incident_id,
        root_cause,
        remediation_action,
        risk_level,
        remediation_plan
    )


def notify_incident(
    incident_id: str,
    incident_type: str,
    severity: str,
    root_cause: Optional[str] = None
) -> bool:
    """
    Convenience function to send incident notification
    """
    slack = SlackIntegration()
    return slack.send_incident_notification(
        incident_id,
        incident_type,
        severity,
        root_cause
    )
