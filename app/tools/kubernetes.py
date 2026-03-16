"""
Kubernetes Diagnostic Tools

Safe, read-only tools for gathering K8s diagnostics.
All tools validate against guardrails before execution.
"""

from typing import Optional
from kubernetes import client, config
from langchain_core.tools import tool
import yaml


def init_k8s_client():
    """Initialize Kubernetes client (in-cluster or kubeconfig)"""
    try:
        # Try in-cluster config first
        config.load_incluster_config()
    except Exception:
        # Fall back to kubeconfig
        config.load_kube_config()
    
    return client.CoreV1Api(), client.AppsV1Api()


@tool
def get_pod_description(namespace: str, pod_name: str) -> str:
    """
    Get detailed pod description including status, events, and configuration.
    
    Args:
        namespace: Kubernetes namespace
        pod_name: Name of the pod
        
    Returns:
        Pod description as YAML string
    """
    
    v1, _ = init_k8s_client()
    
    try:
        pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
        
        # Convert to dict for readability
        pod_dict = {
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "status": {
                "phase": pod.status.phase,
                "conditions": [
                    {
                        "type": c.type,
                        "status": c.status,
                        "reason": c.reason,
                        "message": c.message
                    }
                    for c in (pod.status.conditions or [])
                ],
                "container_statuses": [
                    {
                        "name": cs.name,
                        "ready": cs.ready,
                        "restart_count": cs.restart_count,
                        "state": str(cs.state),
                        "last_state": str(cs.last_state)
                    }
                    for cs in (pod.status.container_statuses or [])
                ]
            },
            "spec": {
                "containers": [
                    {
                        "name": c.name,
                        "image": c.image,
                        "env": [{"name": e.name, "value": e.value} for e in (c.env or [])],
                        "resources": {
                            "requests": c.resources.requests if c.resources else {},
                            "limits": c.resources.limits if c.resources else {}
                        },
                        "liveness_probe": str(c.liveness_probe) if c.liveness_probe else None,
                        "readiness_probe": str(c.readiness_probe) if c.readiness_probe else None
                    }
                    for c in pod.spec.containers
                ]
            }
        }
        
        return yaml.dump(pod_dict, default_flow_style=False)
        
    except client.exceptions.ApiException as e:
        return f"Error: {e.status} - {e.reason}"


@tool
def get_pod_logs(namespace: str, pod_name: str, container: Optional[str] = None, tail_lines: int = 100) -> str:
    """
    Get recent container logs from a pod.
    
    Args:
        namespace: Kubernetes namespace
        pod_name: Name of the pod
        container: Container name (optional, uses first container if not specified)
        tail_lines: Number of recent log lines to retrieve (default: 100)
        
    Returns:
        Container logs as string
    """
    
    v1, _ = init_k8s_client()
    
    try:
        logs = v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            container=container,
            tail_lines=tail_lines,
            timestamps=True
        )
        
        return f"Last {tail_lines} log lines:\n{logs}"
        
    except client.exceptions.ApiException as e:
        return f"Error: {e.status} - {e.reason}"


@tool
def get_pod_events(namespace: str, pod_name: str) -> str:
    """
    Get Kubernetes events related to a pod.
    
    Args:
        namespace: Kubernetes namespace
        pod_name: Name of the pod
        
    Returns:
        List of events as formatted string
    """
    
    v1, _ = init_k8s_client()
    
    try:
        events = v1.list_namespaced_event(
            namespace=namespace,
            field_selector=f"involvedObject.name={pod_name}"
        )
        
        if not events.items:
            return "No events found for this pod"
        
        event_list = []
        for event in sorted(events.items, key=lambda e: e.last_timestamp or e.event_time):
            event_list.append({
                "time": str(event.last_timestamp or event.event_time),
                "type": event.type,
                "reason": event.reason,
                "message": event.message,
                "count": event.count
            })
        
        return yaml.dump(event_list, default_flow_style=False)
        
    except client.exceptions.ApiException as e:
        return f"Error: {e.status} - {e.reason}"


@tool
def get_recent_deployments(namespace: str, deployment_name: str, limit: int = 5) -> str:
    """
    Get recent deployment history and rollout status.
    
    Args:
        namespace: Kubernetes namespace
        deployment_name: Name of the deployment
        limit: Number of recent revisions to retrieve
        
    Returns:
        Deployment history as formatted string
    """
    
    _, apps_v1 = init_k8s_client()
    
    try:
        deployment = apps_v1.read_namespaced_deployment(
            name=deployment_name,
            namespace=namespace
        )
        
        # Get replica sets for this deployment
        v1, _ = init_k8s_client()
        replicasets = apps_v1.list_namespaced_replica_set(
            namespace=namespace,
            label_selector=f"app={deployment.metadata.labels.get('app', '')}"
        )
        
        history = {
            "deployment": deployment_name,
            "current_replicas": deployment.status.replicas,
            "ready_replicas": deployment.status.ready_replicas,
            "updated_replicas": deployment.status.updated_replicas,
            "conditions": [
                {
                    "type": c.type,
                    "status": c.status,
                    "reason": c.reason,
                    "message": c.message
                }
                for c in (deployment.status.conditions or [])
            ],
            "recent_replicasets": [
                {
                    "name": rs.metadata.name,
                    "revision": rs.metadata.annotations.get("deployment.kubernetes.io/revision", "unknown"),
                    "replicas": rs.status.replicas,
                    "created": str(rs.metadata.creation_timestamp)
                }
                for rs in sorted(
                    replicasets.items,
                    key=lambda x: x.metadata.creation_timestamp,
                    reverse=True
                )[:limit]
            ]
        }
        
        return yaml.dump(history, default_flow_style=False)
        
    except client.exceptions.ApiException as e:
        return f"Error: {e.status} - {e.reason}"


@tool
def check_resource_quotas(namespace: str) -> str:
    """
    Check resource quotas and current usage in namespace.
    
    Args:
        namespace: Kubernetes namespace
        
    Returns:
        Resource quota information
    """
    
    v1, _ = init_k8s_client()
    
    try:
        quotas = v1.list_namespaced_resource_quota(namespace=namespace)
        
        if not quotas.items:
            return f"No resource quotas configured for namespace {namespace}"
        
        quota_info = []
        for quota in quotas.items:
            quota_info.append({
                "name": quota.metadata.name,
                "hard_limits": quota.status.hard,
                "current_usage": quota.status.used
            })
        
        return yaml.dump(quota_info, default_flow_style=False)
        
    except client.exceptions.ApiException as e:
        return f"Error: {e.status} - {e.reason}"
