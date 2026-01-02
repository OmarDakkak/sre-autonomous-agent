"""Webhook package for receiving external alerts"""

from app.webhook.server import start_webhook_server

__all__ = ["start_webhook_server"]
