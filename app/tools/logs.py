"""
Log Query Tools

Query logs from Loki or other log aggregation systems.
"""

from typing import Optional
from datetime import datetime, timedelta
from langchain_core.tools import tool
import httpx
import os


def get_loki_url() -> str:
    """Get Loki URL from environment"""
    return os.getenv("LOKI_URL", "http://loki:3100")


@tool
def query_logs_for_errors(namespace: str, pod_name: str, duration: str = "10m", limit: int = 50) -> str:
    """
    Query logs for error patterns.
    
    Args:
        namespace: Kubernetes namespace
        pod_name: Pod name (supports partial match)
        duration: Time range (e.g., "10m", "1h")
        limit: Maximum number of log lines to return
        
    Returns:
        Filtered error logs
    """
    
    loki_url = get_loki_url()
    
    # Convert duration to nanoseconds for Loki
    duration_minutes = int(duration.replace('m', '').replace('h', '')) * (60 if 'h' in duration else 1)
    start_time = datetime.now() - timedelta(minutes=duration_minutes)
    
    # LogQL query for errors
    query = f'{{namespace="{namespace}", pod=~"{pod_name}.*"}} |~ "(?i)(error|exception|fatal|critical)"'
    
    params = {
        "query": query,
        "limit": limit,
        "start": int(start_time.timestamp() * 1e9),
        "end": int(datetime.now().timestamp() * 1e9),
        "direction": "backward"
    }
    
    try:
        response = httpx.get(
            f"{loki_url}/loki/api/v1/query_range",
            params=params,
            timeout=30.0
        )
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get("data", {}).get("result"):
            return f"No error logs found for pod {pod_name} in last {duration}"
        
        logs = []
        for stream in data["data"]["result"]:
            labels = stream.get("stream", {})
            for value in stream.get("values", []):
                timestamp, log_line = value
                logs.append(f"[{labels.get('container', 'unknown')}] {log_line}")
        
        if not logs:
            return "No matching logs found"
        
        return f"Error logs for {pod_name} (last {duration}):\n\n" + "\n".join(logs[:limit])
        
    except Exception as e:
        return f"Error querying Loki: {str(e)}"


@tool
def query_logs_by_pattern(namespace: str, pod_name: str, pattern: str, duration: str = "10m", limit: int = 50) -> str:
    """
    Query logs matching a specific pattern.
    
    Args:
        namespace: Kubernetes namespace
        pod_name: Pod name
        pattern: Regex pattern to search for
        duration: Time range
        limit: Maximum number of log lines
        
    Returns:
        Matching log lines
    """
    
    loki_url = get_loki_url()
    
    duration_minutes = int(duration.replace('m', '').replace('h', '')) * (60 if 'h' in duration else 1)
    start_time = datetime.now() - timedelta(minutes=duration_minutes)
    
    query = f'{{namespace="{namespace}", pod=~"{pod_name}.*"}} |~ "{pattern}"'
    
    params = {
        "query": query,
        "limit": limit,
        "start": int(start_time.timestamp() * 1e9),
        "end": int(datetime.now().timestamp() * 1e9),
        "direction": "backward"
    }
    
    try:
        response = httpx.get(
            f"{loki_url}/loki/api/v1/query_range",
            params=params,
            timeout=30.0
        )
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get("data", {}).get("result"):
            return f"No logs matching pattern '{pattern}' found"
        
        logs = []
        for stream in data["data"]["result"]:
            for value in stream.get("values", []):
                _, log_line = value
                logs.append(log_line)
        
        return f"Logs matching '{pattern}' (last {duration}):\n\n" + "\n".join(logs[:limit])
        
    except Exception as e:
        return f"Error querying Loki: {str(e)}"
