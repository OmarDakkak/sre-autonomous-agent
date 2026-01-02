#!/usr/bin/env python3
"""
Test script to run the SRE agent against the real crashing pod
"""

import json
import os
from datetime import datetime

# Set OpenAI API key (replace with your actual key)
os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY', 'your-key-here')

# Create a simulated alert based on the actual pod
alert = {
    "version": "4",
    "groupKey": "{}:{alertname=\"PodCrashLooping\"}",
    "status": "firing",
    "receiver": "sre-agent",
    "groupLabels": {
        "alertname": "PodCrashLooping"
    },
    "commonLabels": {
        "alertname": "PodCrashLooping",
        "namespace": "payments",
        "pod": "api-594c8fd944-9ddk9",  # Actual pod name from our deployment
        "severity": "critical",
        "cluster": "minikube"
    },
    "commonAnnotations": {
        "description": "Pod payments/api-594c8fd944-9ddk9 is in CrashLoopBackOff state",
        "summary": "Pod has been crashing repeatedly",
        "runbook_url": "https://runbooks.example.com/pod-crashloop"
    },
    "externalURL": "http://localhost",
    "alerts": [
        {
            "status": "firing",
            "labels": {
                "alertname": "PodCrashLooping",
                "namespace": "payments",
                "pod": "api-594c8fd944-9ddk9",
                "deployment": "api",
                "container": "api-server",
                "severity": "critical",
                "cluster": "minikube",
                "app": "payment-api"
            },
            "annotations": {
                "description": "Pod payments/api-594c8fd944-9ddk9 is crashing",
                "summary": "Container in CrashLoopBackOff",
                "impact": "Payment processing unavailable"
            },
            "startsAt": datetime.utcnow().isoformat() + "Z",
            "endsAt": "0001-01-01T00:00:00Z",
            "generatorURL": "http://localhost/prometheus"
        }
    ]
}

print("Testing SRE Autonomous Agent")
print("=" * 80)
print("\nTest Setup:")
print(f"  Cluster: minikube")
print(f"  Namespace: payments")
print(f"  Pod: api-594c8fd944-9ddk9")
print(f"  Expected Issue: Missing DATABASE_URL environment variable")
print("\n" + "=" * 80)

# Save test alert
with open("test-alert.json", "w") as f:
    json.dump(alert, f, indent=2)

print("\nTest alert created: test-alert.json")
print("\nTo run the agent:")
print("   export OPENAI_API_KEY='your-key-here'")
print("   venv/bin/python -m app.main test-alert.json")
print("\n" + "=" * 80)
