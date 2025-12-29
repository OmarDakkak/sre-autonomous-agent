"""
Prometheus Metrics Tools

Query Prometheus for metrics related to incidents.
"""

from typing import Optional, List, Dict
from datetime import datetime, timedelta
from prometheus_api_client import PrometheusConnect
from langchain_core.tools import tool
import os


def get_prometheus_client() -> PrometheusConnect:
    """Initialize Prometheus client from environment"""
    prometheus_url = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
    return PrometheusConnect(url=prometheus_url, disable_ssl=True)


@tool
def query_pod_cpu_usage(namespace: str, pod_name: str, duration: str = "10m") -> str:
    """
    Query CPU usage for a pod over time.
    
    Args:
        namespace: Kubernetes namespace
        pod_name: Pod name (can use partial match)
        duration: Time range (e.g., "10m", "1h")
        
    Returns:
        CPU usage metrics
    """
    
    prom = get_prometheus_client()
    
    query = f'rate(container_cpu_usage_seconds_total{{namespace="{namespace}", pod=~"{pod_name}.*"}}[5m])'
    
    try:
        result = prom.custom_query_range(
            query=query,
            start_time=datetime.now() - timedelta(minutes=int(duration.replace('m', ''))),
            end_time=datetime.now(),
            step="1m"
        )
        
        if not result:
            return f"No CPU metrics found for pod {pod_name} in namespace {namespace}"
        
        # Format results
        output = f"CPU Usage for {pod_name} (last {duration}):\n"
        for metric in result:
            container = metric['metric'].get('container', 'unknown')
            values = metric['values']
            
            avg_cpu = sum(float(v[1]) for v in values) / len(values) if values else 0
            max_cpu = max(float(v[1]) for v in values) if values else 0
            
            output += f"\nContainer: {container}\n"
            output += f"  Average CPU: {avg_cpu:.4f} cores\n"
            output += f"  Peak CPU: {max_cpu:.4f} cores\n"
        
        return output
        
    except Exception as e:
        return f"Error querying Prometheus: {str(e)}"


@tool
def query_pod_memory_usage(namespace: str, pod_name: str, duration: str = "10m") -> str:
    """
    Query memory usage for a pod over time.
    
    Args:
        namespace: Kubernetes namespace
        pod_name: Pod name (can use partial match)
        duration: Time range (e.g., "10m", "1h")
        
    Returns:
        Memory usage metrics
    """
    
    prom = get_prometheus_client()
    
    query = f'container_memory_working_set_bytes{{namespace="{namespace}", pod=~"{pod_name}.*"}}'
    
    try:
        result = prom.custom_query_range(
            query=query,
            start_time=datetime.now() - timedelta(minutes=int(duration.replace('m', ''))),
            end_time=datetime.now(),
            step="1m"
        )
        
        if not result:
            return f"No memory metrics found for pod {pod_name} in namespace {namespace}"
        
        output = f"Memory Usage for {pod_name} (last {duration}):\n"
        for metric in result:
            container = metric['metric'].get('container', 'unknown')
            values = metric['values']
            
            avg_mem = sum(float(v[1]) for v in values) / len(values) if values else 0
            max_mem = max(float(v[1]) for v in values) if values else 0
            
            output += f"\nContainer: {container}\n"
            output += f"  Average Memory: {avg_mem / (1024**3):.2f} GB\n"
            output += f"  Peak Memory: {max_mem / (1024**3):.2f} GB\n"
        
        return output
        
    except Exception as e:
        return f"Error querying Prometheus: {str(e)}"


@tool
def query_pod_restart_count(namespace: str, pod_name: str, duration: str = "1h") -> str:
    """
    Query pod restart count over time.
    
    Args:
        namespace: Kubernetes namespace
        pod_name: Pod name (can use partial match)
        duration: Time range (e.g., "1h", "24h")
        
    Returns:
        Restart count metrics
    """
    
    prom = get_prometheus_client()
    
    query = f'kube_pod_container_status_restarts_total{{namespace="{namespace}", pod=~"{pod_name}.*"}}'
    
    try:
        result = prom.custom_query(query=query)
        
        if not result:
            return f"No restart metrics found for pod {pod_name}"
        
        output = f"Restart Counts for {pod_name}:\n"
        for metric in result:
            container = metric['metric'].get('container', 'unknown')
            restarts = metric['value'][1]
            
            output += f"  {container}: {restarts} restarts\n"
        
        return output
        
    except Exception as e:
        return f"Error querying Prometheus: {str(e)}"


@tool
def query_http_error_rate(namespace: str, service: str, duration: str = "10m") -> str:
    """
    Query HTTP error rate for a service.
    
    Args:
        namespace: Kubernetes namespace
        service: Service name
        duration: Time range
        
    Returns:
        Error rate metrics
    """
    
    prom = get_prometheus_client()
    
    # Assumes standard Istio/Envoy metrics
    query = f'''
    sum(rate(http_requests_total{{namespace="{namespace}", service=~"{service}.*", status=~"5.."}}[5m])) 
    / 
    sum(rate(http_requests_total{{namespace="{namespace}", service=~"{service}.*"}}[5m]))
    '''
    
    try:
        result = prom.custom_query(query=query)
        
        if not result:
            return f"No HTTP metrics found for service {service}"
        
        error_rate = float(result[0]['value'][1]) * 100 if result else 0
        
        return f"HTTP 5xx Error Rate for {service}: {error_rate:.2f}%"
        
    except Exception as e:
        return f"Error querying Prometheus: {str(e)}"
