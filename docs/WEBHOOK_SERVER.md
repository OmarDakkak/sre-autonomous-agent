# Webhook Server Guide

This guide explains how to set up and configure the webhook server to receive alerts from Prometheus Alertmanager, PagerDuty, and other monitoring systems.

## Overview

The webhook server automatically triggers the incident response workflow when it receives alerts from external systems.

**Supported integrations:**
- 🔥 **Prometheus Alertmanager** - Kubernetes monitoring alerts
- 📟 **PagerDuty** - Incident management webhooks
- 🔔 **Generic Webhooks** - Custom alert formats

## Quick Start

### 1. Start the Webhook Server

```bash
# Start with defaults (port 9000)
./run-webhook.sh

# Or specify custom host/port
export WEBHOOK_HOST=0.0.0.0
export WEBHOOK_PORT=8080
./run-webhook.sh
```

The server will start on `http://localhost:9000` by default.

### 2. Configure Alertmanager

Add the webhook receiver to your Alertmanager configuration:

```yaml
# alertmanager.yml
route:
  group_by: ['alertname', 'cluster']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'sre-agent'

receivers:
  - name: 'sre-agent'
    webhook_configs:
      - url: 'http://your-server:9000/webhook/alertmanager'
        send_resolved: false
```

Reload Alertmanager:

```bash
# If running in Kubernetes
kubectl -n monitoring rollout restart deployment alertmanager

# If running as systemd service
systemctl reload alertmanager
```

### 3. Test the Integration

Send a test alert:

```bash
curl -X POST http://localhost:9000/webhook/alertmanager \
  -H 'Content-Type: application/json' \
  -d '{
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
      "summary": "Pod is crash looping",
      "description": "Pod my-app-xyz has restarted 5 times"
    },
    "externalURL": "http://alertmanager:9093",
    "alerts": [{
      "status": "firing",
      "labels": {
        "alertname": "PodCrashLooping",
        "severity": "critical",
        "namespace": "default",
        "pod": "my-app-xyz"
      },
      "annotations": {
        "summary": "Pod is crash looping"
      },
      "startsAt": "2026-01-02T10:30:00Z"
    }]
  }'
```

You should see output indicating the incident is being processed.

## Prometheus Alertmanager Integration

### Webhook Endpoint

```
POST http://your-server:9000/webhook/alertmanager
```

### Alertmanager Payload Format

The webhook server expects the standard Alertmanager webhook format:

```json
{
  "version": "4",
  "groupKey": "string",
  "status": "firing",
  "receiver": "sre-agent",
  "groupLabels": {},
  "commonLabels": {
    "alertname": "PodCrashLooping",
    "severity": "critical",
    "namespace": "default",
    "pod": "my-app-xyz",
    "deployment": "my-app"
  },
  "commonAnnotations": {
    "summary": "Brief description",
    "description": "Detailed description"
  },
  "externalURL": "http://alertmanager:9093",
  "alerts": [
    {
      "status": "firing",
      "labels": {...},
      "annotations": {...},
      "startsAt": "2026-01-02T10:30:00Z",
      "generatorURL": "http://prometheus:9090/..."
    }
  ]
}
```

### Important Labels

The agent uses these labels to identify and diagnose incidents:

- `alertname` - Type of alert (e.g., PodCrashLooping)
- `namespace` - Kubernetes namespace
- `pod` - Pod name
- `deployment` - Deployment name
- `container` - Container name
- `severity` - Severity level (critical, warning, info)

### Example Prometheus Alert Rules

```yaml
# prometheus-rules.yml
groups:
  - name: kubernetes-pods
    interval: 30s
    rules:
      - alert: PodCrashLooping
        expr: rate(kube_pod_container_status_restarts_total[5m]) > 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Pod {{ $labels.namespace }}/{{ $labels.pod }} is crash looping"
          description: "Pod has restarted {{ $value }} times in the last 5 minutes"
      
      - alert: PodNotReady
        expr: kube_pod_status_phase{phase!="Running"} == 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Pod {{ $labels.namespace }}/{{ $labels.pod }} is not ready"
          description: "Pod is in {{ $labels.phase }} state"
```

## PagerDuty Integration

### Webhook Endpoint

```
POST http://your-server:9000/webhook/pagerduty
```

### Setup in PagerDuty

1. Go to **Services** → Select your service
2. Click **Integrations** tab
3. Click **Add Integration**
4. Select **Generic Webhooks (v3)**
5. Enter webhook URL: `http://your-server:9000/webhook/pagerduty`
6. Click **Add**

### PagerDuty Payload Format

The webhook server handles PagerDuty webhook payloads:

```json
{
  "messages": [
    {
      "event": "incident.trigger",
      "incident": {
        "incident_key": "srv01/HTTP",
        "title": "Production API Down",
        "service": {
          "name": "Production API"
        },
        "urgency": "high",
        "body": {
          "details": "API endpoint returning 500 errors"
        },
        "html_url": "https://acme.pagerduty.com/incidents/ABC123",
        "created_at": "2026-01-02T10:30:00Z"
      }
    }
  ]
}
```

## Generic Webhook Integration

### Webhook Endpoint

```
POST http://your-server:9000/webhook/alert
```

### Custom Alert Format

For custom monitoring systems, use the generic endpoint with this format:

```json
{
  "status": "firing",
  "commonLabels": {
    "alertname": "CustomAlert",
    "severity": "critical",
    "namespace": "default",
    "service": "my-service"
  },
  "commonAnnotations": {
    "summary": "Brief description",
    "description": "Detailed description of the issue"
  },
  "startsAt": "2026-01-02T10:30:00Z"
}
```

### Example: Datadog Integration

```python
# Datadog webhook handler
import requests

def send_to_agent(alert):
    webhook_url = "http://your-server:9000/webhook/alert"
    
    payload = {
        "status": "firing",
        "commonLabels": {
            "alertname": alert["alert_name"],
            "severity": alert["priority"],
            "namespace": alert.get("namespace", "default")
        },
        "commonAnnotations": {
            "summary": alert["title"],
            "description": alert["body"]
        },
        "startsAt": alert["date"]
    }
    
    response = requests.post(webhook_url, json=payload)
    return response.json()
```

## Deployment

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 9000

CMD ["python", "-m", "app.webhook.server"]
```

Build and run:

```bash
docker build -t sre-agent-webhook .
docker run -p 9000:9000 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e SLACK_WEBHOOK_URL=$SLACK_WEBHOOK_URL \
  -v $(pwd)/approvals:/app/approvals \
  -v $(pwd)/postmortems:/app/postmortems \
  sre-agent-webhook
```

### Kubernetes Deployment

```yaml
# webhook-deployment.yaml
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
        - name: SLACK_WEBHOOK_URL
          valueFrom:
            secretKeyRef:
              name: sre-agent-secrets
              key: slack-webhook-url
        - name: WEBHOOK_HOST
          value: "0.0.0.0"
        - name: WEBHOOK_PORT
          value: "9000"
        volumeMounts:
        - name: approvals
          mountPath: /app/approvals
        - name: postmortems
          mountPath: /app/postmortems
      volumes:
      - name: approvals
        persistentVolumeClaim:
          claimName: sre-agent-approvals
      - name: postmortems
        persistentVolumeClaim:
          claimName: sre-agent-postmortems
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
  type: ClusterIP
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: sre-agent-webhook
  namespace: monitoring
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - sre-webhook.example.com
    secretName: sre-webhook-tls
  rules:
  - host: sre-webhook.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: sre-agent-webhook
            port:
              number: 9000
```

Apply:

```bash
kubectl apply -f webhook-deployment.yaml
```

### RBAC Configuration

```yaml
# rbac.yaml
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
  resources: ["deployments", "replicasets"]
  verbs: ["get", "list", "watch", "patch", "update"]
- apiGroups: [""]
  resources: ["namespaces"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: sre-agent
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: sre-agent
subjects:
- kind: ServiceAccount
  name: sre-agent
  namespace: monitoring
```

## Monitoring the Webhook Server

### Health Check

```bash
curl http://localhost:9000/health
```

Response:

```json
{
  "status": "healthy",
  "timestamp": "2026-01-02T10:30:00Z"
}
```

### Prometheus Metrics (Coming Soon)

The webhook server will expose metrics at `/metrics`:

- `webhook_requests_total` - Total webhook requests received
- `webhook_requests_duration_seconds` - Request duration histogram
- `incidents_processed_total` - Total incidents processed
- `incidents_errors_total` - Total processing errors

## Troubleshooting

### Webhook not receiving alerts

1. **Check Alertmanager is reaching the webhook:**
   ```bash
   # Check Alertmanager logs
   kubectl -n monitoring logs -l app=alertmanager
   ```

2. **Verify webhook URL is accessible:**
   ```bash
   curl http://your-server:9000/health
   ```

3. **Check firewall rules** - Ensure port 9000 is open

### Incidents not processing

1. **Check webhook server logs:**
   ```bash
   # If running locally
   tail -f webhook.log
   
   # If running in Kubernetes
   kubectl -n monitoring logs -l app=sre-agent-webhook -f
   ```

2. **Verify OpenAI API key is set:**
   ```bash
   echo $OPENAI_API_KEY
   ```

3. **Check Kubernetes permissions:**
   ```bash
   kubectl auth can-i get pods --as=system:serviceaccount:monitoring:sre-agent
   ```

### Performance Issues

- **Increase replicas** if processing many alerts
- **Add resource limits** to prevent OOM
- **Use persistent storage** for approvals/postmortems
- **Enable caching** for frequently accessed data

## Security Best Practices

1. **Use HTTPS** - Configure TLS certificates
2. **Authenticate requests** - Validate webhook signatures
3. **Rate limiting** - Prevent abuse
4. **Network policies** - Restrict access to webhook endpoint
5. **Secrets management** - Use Kubernetes secrets or vault

## Example: Complete Setup

```bash
# 1. Start webhook server locally
./run-webhook.sh &

# 2. Expose with ngrok for testing
ngrok http 9000

# 3. Configure Alertmanager
cat <<EOF > /etc/alertmanager/alertmanager.yml
receivers:
  - name: 'sre-agent'
    webhook_configs:
      - url: 'https://your-ngrok-url.ngrok.io/webhook/alertmanager'
EOF

# 4. Reload Alertmanager
curl -X POST http://localhost:9093/-/reload

# 5. Test with sample alert
curl -X POST https://your-ngrok-url.ngrok.io/webhook/alertmanager \
  -H 'Content-Type: application/json' \
  -d @examples/crashloop_alert.json

# 6. Monitor logs
tail -f webhook.log
```

## Resources

- [Prometheus Alertmanager Documentation](https://prometheus.io/docs/alerting/latest/configuration/)
- [PagerDuty Webhooks](https://developer.pagerduty.com/docs/webhooks/v3-overview/)
- [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
