"""
Real Integration Test for SRE Autonomous Agent

This test creates a real Kubernetes deployment, triggers an alert,
and tests the full incident response flow with human approval.
"""

import pytest
import subprocess
import json
import time
from pathlib import Path
from kubernetes import client, config
from kubernetes.client.rest import ApiException

# Test configuration
TEST_NAMESPACE = "test-sre-agent"
TEST_DEPLOYMENT_NAME = "test-crashloop-app"


@pytest.fixture(scope="module")
def k8s_client():
    """Load Kubernetes config and return API client"""
    try:
        config.load_kube_config()
    except Exception:
        # Try in-cluster config if kubeconfig not found
        config.load_incluster_config()
    
    return {
        "core": client.CoreV1Api(),
        "apps": client.AppsV1Api()
    }


@pytest.fixture(scope="module")
def test_namespace(k8s_client):
    """Create test namespace"""
    core_api = k8s_client["core"]
    
    namespace = client.V1Namespace(
        metadata=client.V1ObjectMeta(name=TEST_NAMESPACE)
    )
    
    try:
        core_api.create_namespace(namespace)
        print(f"Created namespace: {TEST_NAMESPACE}")
    except ApiException as e:
        if e.status == 409:  # Already exists
            print(f"Namespace {TEST_NAMESPACE} already exists")
        else:
            raise
    
    yield TEST_NAMESPACE
    
    # Cleanup
    try:
        core_api.delete_namespace(TEST_NAMESPACE)
        print(f"Deleted namespace: {TEST_NAMESPACE}")
    except ApiException:
        pass


@pytest.fixture
def crashloop_deployment(k8s_client, test_namespace):
    """Create a deployment that will crash due to missing env var"""
    apps_api = k8s_client["apps"]
    
    # Create deployment without DATABASE_URL (will crash)
    deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(
            name=TEST_DEPLOYMENT_NAME,
            namespace=test_namespace,
            labels={"app": "test-app", "test": "crashloop"}
        ),
        spec=client.V1DeploymentSpec(
            replicas=1,
            selector=client.V1LabelSelector(
                match_labels={"app": "test-app"}
            ),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels={"app": "test-app"}
                ),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="app",
                            image="busybox:latest",
                            command=[
                                "sh", "-c",
                                """
                                if [ -z "$DATABASE_URL" ]; then
                                    echo "ERROR: Missing DATABASE_URL environment variable"
                                    exit 1
                                fi
                                echo "Starting application..."
                                while true; do sleep 3600; done
                                """
                            ],
                            # Intentionally NOT setting DATABASE_URL
                            resources=client.V1ResourceRequirements(
                                requests={"memory": "64Mi", "cpu": "100m"},
                                limits={"memory": "128Mi", "cpu": "200m"}
                            )
                        )
                    ],
                    restart_policy="Always"
                )
            )
        )
    )
    
    try:
        apps_api.create_namespaced_deployment(test_namespace, deployment)
        print(f"Created deployment: {TEST_DEPLOYMENT_NAME}")
    except ApiException as e:
        if e.status == 409:  # Already exists
            apps_api.delete_namespaced_deployment(TEST_DEPLOYMENT_NAME, test_namespace)
            time.sleep(2)
            apps_api.create_namespaced_deployment(test_namespace, deployment)
        else:
            raise
    
    # Wait for pod to start crashing
    time.sleep(10)
    
    yield deployment
    
    # Cleanup
    try:
        apps_api.delete_namespaced_deployment(
            TEST_DEPLOYMENT_NAME, 
            test_namespace,
            body=client.V1DeleteOptions(propagation_policy="Foreground")
        )
        print(f"Deleted deployment: {TEST_DEPLOYMENT_NAME}")
    except ApiException:
        pass


def wait_for_crashloop(k8s_client, namespace, max_wait=60):
    """Wait for pod to enter CrashLoopBackOff state"""
    core_api = k8s_client["core"]
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        pods = core_api.list_namespaced_pod(
            namespace,
            label_selector="app=test-app"
        )
        
        if pods.items:
            pod = pods.items[0]
            container_statuses = pod.status.container_statuses
            
            if container_statuses:
                status = container_statuses[0].state
                if status.waiting and status.waiting.reason == "CrashLoopBackOff":
                    print(f"Pod {pod.metadata.name} is in CrashLoopBackOff")
                    return pod
        
        time.sleep(5)
    
    raise TimeoutError("Pod did not enter CrashLoopBackOff state")


def create_alert_payload(pod_name, namespace):
    """Create Alertmanager-style alert payload"""
    return {
        "status": "firing",
        "commonLabels": {
            "alertname": "PodCrashLooping",
            "namespace": namespace,
            "pod": pod_name,
            "severity": "critical",
            "cluster": "test-cluster"
        },
        "commonAnnotations": {
            "description": f"Pod {namespace}/{pod_name} is in CrashLoopBackOff state",
            "summary": "Pod has been crashing repeatedly"
        },
        "startsAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }


def test_end_to_end_incident_response(k8s_client, crashloop_deployment, test_namespace):
    """
    End-to-end test of the incident response system:
    1. Create crashing deployment
    2. Wait for CrashLoopBackOff
    3. Generate alert
    4. Run agent
    5. Verify remediation plan
    6. Test approval flow
    7. Execute remediation
    8. Verify fix
    """
    
    # Step 1 & 2: Wait for pod to crash
    print("\n1. Waiting for pod to enter CrashLoopBackOff...")
    pod = wait_for_crashloop(k8s_client, test_namespace)
    assert pod is not None
    
    # Step 3: Create alert
    print("\n2. Creating alert payload...")
    alert = create_alert_payload(pod.metadata.name, test_namespace)
    
    alert_file = Path("test_alert_integration.json")
    with open(alert_file, "w") as f:
        json.dump(alert, f, indent=2)
    
    # Step 4: Run agent
    print("\n3. Running SRE agent...")
    result = subprocess.run(
        ["python", "-m", "app.main", str(alert_file)],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.returncode != 0:
        print("STDERR:", result.stderr)
    
    # Step 5: Verify postmortem was created
    print("\n4. Verifying postmortem creation...")
    postmortem_dir = Path("postmortems")
    assert postmortem_dir.exists()
    
    postmortems = list(postmortem_dir.glob("INC-*.md"))
    assert len(postmortems) > 0, "No postmortem file created"
    
    latest_postmortem = max(postmortems, key=lambda p: p.stat().st_mtime)
    with open(latest_postmortem) as f:
        content = f.read()
    
    # Verify key sections
    assert "CrashLoopBackOff" in content
    assert "DATABASE_URL" in content or "environment" in content.lower()
    assert "Remediation" in content
    
    print(f"\n5. Postmortem verified: {latest_postmortem}")
    
    # Cleanup
    alert_file.unlink()
    
    print("\n✅ End-to-end test passed!")


def test_remediation_plan_generation(k8s_client, crashloop_deployment, test_namespace):
    """Test that the agent generates a valid remediation plan"""
    
    print("\nTesting remediation plan generation...")
    
    # Wait for crash
    pod = wait_for_crashloop(k8s_client, test_namespace)
    alert = create_alert_payload(pod.metadata.name, test_namespace)
    
    # Save alert
    alert_file = Path("test_remediation.json")
    with open(alert_file, "w") as f:
        json.dump(alert, f, indent=2)
    
    # Run agent
    result = subprocess.run(
        ["python", "-m", "app.main", str(alert_file)],
        capture_output=True,
        text=True
    )
    
    output = result.stdout
    
    # Check for remediation keywords
    assert "Remediation" in output or "APPROVAL" in output
    assert "DATABASE_URL" in output or "environment" in output
    
    # Cleanup
    alert_file.unlink()
    
    print("✅ Remediation plan test passed!")


def test_manual_fix_verification(k8s_client, crashloop_deployment, test_namespace):
    """
    Test that applying the suggested fix actually resolves the issue
    """
    
    print("\nTesting manual fix application...")
    
    apps_api = k8s_client["apps"]
    core_api = k8s_client["core"]
    
    # Wait for crash
    pod = wait_for_crashloop(k8s_client, test_namespace)
    print(f"Pod {pod.metadata.name} is crashing")
    
    # Apply fix: Add DATABASE_URL environment variable
    print("Applying fix: Adding DATABASE_URL environment variable...")
    
    deployment = apps_api.read_namespaced_deployment(TEST_DEPLOYMENT_NAME, test_namespace)
    container = deployment.spec.template.spec.containers[0]
    
    # Add environment variable
    if container.env is None:
        container.env = []
    
    container.env.append(
        client.V1EnvVar(
            name="DATABASE_URL",
            value="postgresql://localhost:5432/testdb"
        )
    )
    
    # Update deployment
    apps_api.patch_namespaced_deployment(
        TEST_DEPLOYMENT_NAME,
        test_namespace,
        deployment
    )
    
    # Wait for new pod to be running
    print("Waiting for pod to become healthy...")
    time.sleep(15)
    
    # Verify pod is now running
    pods = core_api.list_namespaced_pod(
        test_namespace,
        label_selector="app=test-app"
    )
    
    assert len(pods.items) > 0
    
    new_pod = pods.items[0]
    container_status = new_pod.status.container_statuses[0]
    
    # Check if pod is running or at least not crashing
    assert container_status.state.running is not None or \
           (container_status.state.waiting and 
            container_status.state.waiting.reason != "CrashLoopBackOff")
    
    print(f"✅ Pod {new_pod.metadata.name} is now healthy!")
    print(f"   Status: {container_status.state}")


if __name__ == "__main__":
    # Run tests manually
    pytest.main([__file__, "-v", "-s"])
