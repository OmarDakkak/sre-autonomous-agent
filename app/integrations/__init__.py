"""Integrations package for external services"""

from app.integrations.slack import SlackIntegration, send_approval_to_slack, notify_incident

__all__ = ["SlackIntegration", "send_approval_to_slack", "notify_incident"]
