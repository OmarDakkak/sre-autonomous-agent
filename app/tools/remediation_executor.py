"""
Remediation Executor

Executes approved remediation actions on Kubernetes clusters.
Includes rollback capability for safety.
"""

import subprocess
import time
from typing import Dict, Any, Optional, Tuple
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from pathlib import Path
import json
from datetime import datetime


class RemediationExecutor:
    """Executes remediation actions with rollback capability"""
    
    def __init__(self):
        try:
            config.load_kube_config()
        except:
            config.load_incluster_config()
        
        self.apps_api = client.AppsV1Api()
        self.core_api = client.CoreV1Api()
        
        # Store rollback data
        self.rollback_dir = Path("rollbacks")
        self.rollback_dir.mkdir(exist_ok=True)
    
    def execute_remediation(
        self, 
        incident_id: str,
        remediation_plan: Dict[str, Any],
        alert_data: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Execute an approved remediation action
        
        Returns:
            (success: bool, message: str)
        """
        
        action_type = remediation_plan.get("action_type", "")
        namespace = alert_data.get("commonLabels", {}).get("namespace", "default")
        
        print(f"\n{'='*80}")
        print(f"EXECUTING REMEDIATION: {incident_id}")
        print(f"{'='*80}")
        print(f"Action: {remediation_plan.get('description')}")
        print(f"Namespace: {namespace}")
        print(f"Risk Level: {remediation_plan.get('risk_level')}")
        
        try:
            if action_type == "config_change":
                return self._apply_config_change(incident_id, remediation_plan, alert_data)
            
            elif action_type == "restart_deployment":
                return self._restart_deployment(incident_id, remediation_plan, alert_data)
            
            elif action_type == "scale_deployment":
                return self._scale_deployment(incident_id, remediation_plan, alert_data)
            
            elif action_type == "rollback_deployment":
                return self._rollback_deployment(incident_id, remediation_plan, alert_data)
            
            else:
                return False, f"Unknown action type: {action_type}"
        
        except Exception as e:
            return False, f"Execution failed: {str(e)}"
    
    def _apply_config_change(
        self,
        incident_id: str,
        remediation_plan: Dict[str, Any],
        alert_data: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Apply configuration change (e.g., add environment variable)
        """
        namespace = alert_data.get("commonLabels", {}).get("namespace", "default")
        deployment_name = alert_data.get("commonLabels", {}).get("deployment")
        
        if not deployment_name:
            # Try to get from pod name
            pod_name = alert_data.get("commonLabels", {}).get("pod", "")
            deployment_name = "-".join(pod_name.split("-")[:-2]) if pod_name else None
        
        if not deployment_name:
            return False, "Could not determine deployment name"
        
        print(f"Applying config change to deployment: {deployment_name}")
        
        try:
            # Read current deployment
            deployment = self.apps_api.read_namespaced_deployment(
                deployment_name, 
                namespace
            )
            
            # Save for rollback
            self._save_rollback_data(incident_id, deployment)
            
            # Apply the change based on remediation plan
            container = deployment.spec.template.spec.containers[0]
            
            # Example: Add DATABASE_URL if missing
            if "DATABASE_URL" in remediation_plan.get("description", ""):
                if container.env is None:
                    container.env = []
                
                # Check if already exists
                existing = [e for e in container.env if e.name == "DATABASE_URL"]
                if not existing:
                    container.env.append(
                        client.V1EnvVar(
                            name="DATABASE_URL",
                            value=remediation_plan.get("value", "postgresql://localhost:5432/db")
                        )
                    )
                    print("Added DATABASE_URL environment variable")
            
            # Update deployment
            self.apps_api.patch_namespaced_deployment(
                deployment_name,
                namespace,
                deployment
            )
            
            # Wait for rollout
            print("Waiting for deployment rollout...")
            time.sleep(5)
            
            # Verify pods are healthy
            if self._verify_deployment_health(deployment_name, namespace):
                return True, f"Successfully applied config change to {deployment_name}"
            else:
                # Rollback if unhealthy
                print("Deployment unhealthy, rolling back...")
                self.rollback(incident_id)
                return False, "Deployment became unhealthy, rolled back changes"
        
        except ApiException as e:
            return False, f"Kubernetes API error: {e.reason}"
    
    def _restart_deployment(
        self,
        incident_id: str,
        remediation_plan: Dict[str, Any],
        alert_data: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Restart a deployment by updating restart annotation"""
        namespace = alert_data.get("commonLabels", {}).get("namespace", "default")
        deployment_name = alert_data.get("commonLabels", {}).get("deployment")
        
        if not deployment_name:
            pod_name = alert_data.get("commonLabels", {}).get("pod", "")
            deployment_name = "-".join(pod_name.split("-")[:-2]) if pod_name else None
        
        if not deployment_name:
            return False, "Could not determine deployment name"
        
        print(f"Restarting deployment: {deployment_name}")
        
        try:
            deployment = self.apps_api.read_namespaced_deployment(
                deployment_name,
                namespace
            )
            
            # Add restart annotation
            if deployment.spec.template.metadata.annotations is None:
                deployment.spec.template.metadata.annotations = {}
            
            deployment.spec.template.metadata.annotations[
                "kubectl.kubernetes.io/restartedAt"
            ] = datetime.utcnow().isoformat()
            
            self.apps_api.patch_namespaced_deployment(
                deployment_name,
                namespace,
                deployment
            )
            
            return True, f"Successfully restarted deployment {deployment_name}"
        
        except ApiException as e:
            return False, f"Failed to restart: {e.reason}"
    
    def _scale_deployment(
        self,
        incident_id: str,
        remediation_plan: Dict[str, Any],
        alert_data: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Scale a deployment"""
        namespace = alert_data.get("commonLabels", {}).get("namespace", "default")
        deployment_name = alert_data.get("commonLabels", {}).get("deployment")
        replicas = remediation_plan.get("replicas", 1)
        
        if not deployment_name:
            return False, "Could not determine deployment name"
        
        print(f"Scaling deployment {deployment_name} to {replicas} replicas")
        
        try:
            deployment = self.apps_api.read_namespaced_deployment(
                deployment_name,
                namespace
            )
            
            # Save for rollback
            self._save_rollback_data(incident_id, deployment)
            
            deployment.spec.replicas = replicas
            
            self.apps_api.patch_namespaced_deployment(
                deployment_name,
                namespace,
                deployment
            )
            
            return True, f"Successfully scaled {deployment_name} to {replicas} replicas"
        
        except ApiException as e:
            return False, f"Failed to scale: {e.reason}"
    
    def _rollback_deployment(
        self,
        incident_id: str,
        remediation_plan: Dict[str, Any],
        alert_data: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Rollback a deployment to previous version"""
        namespace = alert_data.get("commonLabels", {}).get("namespace", "default")
        deployment_name = alert_data.get("commonLabels", {}).get("deployment")
        
        if not deployment_name:
            return False, "Could not determine deployment name"
        
        print(f"Rolling back deployment: {deployment_name}")
        
        try:
            # Use kubectl rollout undo
            result = subprocess.run(
                [
                    "kubectl", "rollout", "undo",
                    f"deployment/{deployment_name}",
                    "-n", namespace
                ],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return True, f"Successfully rolled back {deployment_name}"
            else:
                return False, f"Rollback failed: {result.stderr}"
        
        except Exception as e:
            return False, f"Rollback failed: {str(e)}"
    
    def _save_rollback_data(self, incident_id: str, deployment):
        """Save deployment state for rollback"""
        rollback_file = self.rollback_dir / f"{incident_id}.json"
        
        data = {
            "incident_id": incident_id,
            "timestamp": datetime.utcnow().isoformat(),
            "deployment_name": deployment.metadata.name,
            "namespace": deployment.metadata.namespace,
            "spec": client.ApiClient().sanitize_for_serialization(deployment.spec)
        }
        
        with open(rollback_file, "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"Saved rollback data to {rollback_file}")
    
    def rollback(self, incident_id: str) -> Tuple[bool, str]:
        """Rollback a remediation using saved state"""
        rollback_file = self.rollback_dir / f"{incident_id}.json"
        
        if not rollback_file.exists():
            return False, "No rollback data found"
        
        with open(rollback_file) as f:
            data = json.load(f)
        
        deployment_name = data["deployment_name"]
        namespace = data["namespace"]
        
        print(f"Rolling back {deployment_name} in {namespace}...")
        
        try:
            # Read current deployment
            deployment = self.apps_api.read_namespaced_deployment(
                deployment_name,
                namespace
            )
            
            # Restore spec from saved data
            deployment.spec = client.ApiClient()._ApiClient__deserialize(
                data["spec"],
                "V1DeploymentSpec"
            )
            
            # Apply
            self.apps_api.replace_namespaced_deployment(
                deployment_name,
                namespace,
                deployment
            )
            
            return True, f"Successfully rolled back {deployment_name}"
        
        except Exception as e:
            return False, f"Rollback failed: {str(e)}"
    
    def _verify_deployment_health(
        self,
        deployment_name: str,
        namespace: str,
        timeout: int = 60
    ) -> bool:
        """Verify that deployment is healthy after change"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                deployment = self.apps_api.read_namespaced_deployment(
                    deployment_name,
                    namespace
                )
                
                # Check if desired replicas match ready replicas
                if deployment.status.ready_replicas == deployment.spec.replicas:
                    print(f"Deployment {deployment_name} is healthy")
                    return True
                
                time.sleep(5)
            
            except ApiException:
                time.sleep(5)
        
        print(f"Deployment {deployment_name} did not become healthy within {timeout}s")
        return False


def execute_approved_remediation(
    incident_id: str,
    remediation_plan: Dict[str, Any],
    alert_data: Dict[str, Any]
) -> Tuple[bool, str]:
    """
    Convenience function to execute approved remediation
    """
    executor = RemediationExecutor()
    return executor.execute_remediation(incident_id, remediation_plan, alert_data)
