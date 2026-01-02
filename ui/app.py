"""
Streamlit Web UI for SRE Autonomous Agent

A modern dashboard for monitoring incidents, submitting alerts,
and managing the autonomous incident response system.
"""

import streamlit as st
import json
import os
import time
from pathlib import Path
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional

# Must be first Streamlit command
st.set_page_config(
    page_title="SRE Autonomous Agent",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
    .incident-card {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
        background: #f8f9fa;
    }
    .severity-critical {
        color: #dc3545;
        font-weight: bold;
    }
    .severity-warning {
        color: #ffc107;
        font-weight: bold;
    }
    .severity-info {
        color: #17a2b8;
        font-weight: bold;
    }
    .status-resolved {
        color: #28a745;
        font-weight: bold;
    }
    .status-investigating {
        color: #fd7e14;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=30)  # Cache for 30 seconds
def load_postmortems():
    """Load all postmortem files"""
    postmortem_dir = Path("postmortems")
    if not postmortem_dir.exists():
        return []
    
    postmortems = []
    for file in postmortem_dir.glob("*.md"):
        with open(file, 'r') as f:
            content = f.read()
            # Parse basic info from filename and content
            incident_id = file.stem
            postmortems.append({
                "id": incident_id,
                "file": str(file),
                "content": content,
                "timestamp": datetime.fromtimestamp(file.stat().st_mtime)
            })
    
    return sorted(postmortems, key=lambda x: x['timestamp'], reverse=True)


@st.cache_data(ttl=60)  # Cache for 60 seconds
def load_example_alerts():
    """Load example alert templates"""
    examples_dir = Path("examples")
    if not examples_dir.exists():
        return {}
    
    alerts = {}
    for file in examples_dir.glob("*.json"):
        with open(file, 'r') as f:
            alerts[file.stem] = json.load(f)
    
    return alerts


def save_alert(alert_data: dict, filename: str):
    """Save alert to file"""
    alerts_dir = Path("alerts")
    alerts_dir.mkdir(exist_ok=True)
    
    filepath = alerts_dir / f"{filename}.json"
    with open(filepath, 'w') as f:
        json.dump(alert_data, f, indent=2)
    
    return filepath


def run_agent_on_alert(alert_file: str):
    """Run the SRE agent on an alert file"""
    import subprocess
    
    result = subprocess.run(
        ["python", "-m", "app.main", alert_file],
        capture_output=True,
        text=True
    )
    
    return result.stdout, result.stderr, result.returncode


def render_sidebar():
    """Render sidebar navigation"""
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/000000/bot.png", width=80)
        st.title("SRE Agent")
        st.markdown("---")
        
        page = st.radio(
            "Navigation",
            ["Dashboard", "Submit Alert", "Incidents", "Approvals", "Postmortems", "Settings"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        st.markdown("### Quick Stats")
        
        postmortems = load_postmortems()
        st.metric("Total Incidents", len(postmortems))
        
        if postmortems:
            recent = postmortems[0]
            st.metric("Last Incident", recent['timestamp'].strftime("%Y-%m-%d"))
        
        st.markdown("---")
        st.markdown("### System Status")
        st.success("Agent Active")
        st.info("Monitoring Enabled")
        
    return page


def render_dashboard():
    """Render main dashboard page"""
    st.markdown('<h1 class="main-header">SRE Autonomous Agent Dashboard</h1>', unsafe_allow_html=True)
    st.markdown("Real-time incident response powered by AI")
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    postmortems = load_postmortems()
    
    with col1:
        st.metric("Total Incidents", len(postmortems), delta=None)
    
    with col2:
        st.metric("Active Incidents", 0, delta="0")
    
    with col3:
        st.metric("Resolved Today", 0, delta="+0")
    
    with col4:
        st.metric("MTTR (avg)", "N/A", delta=None)
    
    st.markdown("---")
    
    # Recent activity
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Recent Incidents")
        
        if postmortems:
            for pm in postmortems[:5]:
                with st.container():
                    st.markdown(f"**{pm['id']}**")
                    st.caption(f"{pm['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    if st.button("View Details", key=pm['id']):
                        st.session_state['selected_incident'] = pm['id']
                        st.rerun()
                    
                    st.markdown("---")
        else:
            st.info("No incidents recorded yet. Submit an alert to get started!")
    
    with col2:
        st.subheader("Alert Sources")
        
        # Mock data for visualization
        sources_data = {
            "Source": ["Prometheus", "Alertmanager", "PagerDuty", "Manual"],
            "Count": [0, 0, 0, 0]
        }
        df = pd.DataFrame(sources_data)
        
        fig = px.pie(df, values='Count', names='Source', 
                     title='Alerts by Source',
                     color_discrete_sequence=px.colors.qualitative.Set3)
        st.plotly_chart(fig, use_container_width=True)


def render_submit_alert():
    """Render alert submission page"""
    st.markdown('<h1 class="main-header">Submit Alert</h1>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["Manual Entry", "Template", "JSON Upload"])
    
    with tab1:
        st.subheader("Create Alert Manually")
        
        col1, col2 = st.columns(2)
        
        with col1:
            alert_name = st.text_input("Alert Name *", placeholder="e.g., PodCrashLooping")
            severity = st.selectbox("Severity *", ["critical", "warning", "info"])
            namespace = st.text_input("Namespace *", placeholder="e.g., production")
            pod_name = st.text_input("Pod Name", placeholder="e.g., myapp-7d4f9c6b5-abc123")
        
        with col2:
            cluster = st.text_input("Cluster", placeholder="e.g., prod-us-east-1")
            description = st.text_area("Description", placeholder="Describe the issue...")
            firing_since = st.text_input("Firing Since", value=datetime.utcnow().isoformat() + "Z")
        
        if st.button("Submit Alert", type="primary"):
            if alert_name and severity and namespace:
                alert_data = {
                    "status": "firing",
                    "commonLabels": {
                        "alertname": alert_name,
                        "severity": severity,
                        "namespace": namespace,
                        "pod": pod_name or "unknown",
                        "cluster": cluster or "default"
                    },
                    "commonAnnotations": {
                        "description": description or f"{alert_name} detected in {namespace}",
                        "summary": f"{severity.upper()}: {alert_name}"
                    },
                    "startsAt": firing_since
                }
                
                # Save alert
                timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
                filename = f"manual-{timestamp}"
                filepath = save_alert(alert_data, filename)
                
                st.success(f"Alert saved: {filepath}")
                
                # Run agent
                with st.spinner("Agent is analyzing the incident..."):
                    stdout, stderr, returncode = run_agent_on_alert(str(filepath))
                    
                    if returncode == 0:
                        st.success("Incident analysis complete!")
                        with st.expander("View Agent Output"):
                            st.code(stdout)
                    else:
                        st.error("Agent encountered an error")
                        with st.expander("View Error Details"):
                            st.code(stderr)
            else:
                st.error("Please fill in all required fields (*)")
    
    with tab2:
        st.subheader("Use Example Template")
        
        examples = load_example_alerts()
        
        if examples:
            selected_template = st.selectbox("Select Template", list(examples.keys()))
            
            if selected_template:
                st.json(examples[selected_template])
                
                if st.button("Run with This Template", type="primary"):
                    example_file = f"examples/{selected_template}.json"
                    
                    with st.spinner("Agent is analyzing the incident..."):
                        stdout, stderr, returncode = run_agent_on_alert(example_file)
                        
                        if returncode == 0:
                            st.success("Incident analysis complete!")
                            with st.expander("View Agent Output"):
                                st.code(stdout)
                        else:
                            st.error("❌ Agent encountered an error")
                            with st.expander("View Error Details"):
                                st.code(stderr)
        else:
            st.info("No example templates found in /examples directory")
    
    with tab3:
        st.subheader("Upload JSON Alert")
        
        uploaded_file = st.file_uploader("Choose a JSON file", type=['json'])
        
        if uploaded_file:
            try:
                alert_data = json.load(uploaded_file)
                st.json(alert_data)
                
                if st.button("Process This Alert", type="primary"):
                    # Save and process
                    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
                    filename = f"uploaded-{timestamp}"
                    filepath = save_alert(alert_data, filename)
                    
                    with st.spinner("Agent is analyzing the incident..."):
                        stdout, stderr, returncode = run_agent_on_alert(str(filepath))
                        
                        if returncode == 0:
                            st.success("Incident analysis complete!")
                            with st.expander("View Agent Output"):
                                st.code(stdout)
                        else:
                            st.error("❌ Agent encountered an error")
                            with st.expander("View Error Details"):
                                st.code(stderr)
                
            except json.JSONDecodeError:
                st.error("Invalid JSON file")


def render_incidents():
    """Render incidents monitoring page"""
    st.markdown('<h1 class="main-header">Incident History</h1>', unsafe_allow_html=True)
    
    postmortems = load_postmortems()
    
    if not postmortems:
        st.info("No incidents recorded yet.")
        return
    
    # Create timeline chart
    df = pd.DataFrame([
        {
            "Incident": pm['id'],
            "Timestamp": pm['timestamp'],
            "Date": pm['timestamp'].strftime("%Y-%m-%d")
        }
        for pm in postmortems
    ])
    
    # Group by date
    daily_counts = df.groupby("Date").size().reset_index(name='Count')
    
    fig = px.bar(daily_counts, x='Date', y='Count',
                 title='Incidents Over Time',
                 labels={'Count': 'Number of Incidents', 'Date': 'Date'},
                 color='Count',
                 color_continuous_scale='Reds')
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Incident list
    st.subheader("All Incidents")
    
    for pm in postmortems:
        with st.expander(f"{pm['id']} - {pm['timestamp'].strftime('%Y-%m-%d %H:%M')}"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(pm['content'][:500] + "..." if len(pm['content']) > 500 else pm['content'])
            
            with col2:
                if st.button("View Full Report", key=f"view_{pm['id']}"):
                    st.session_state['selected_postmortem'] = pm['id']
                    st.rerun()

def render_approvals():
    """Render approvals page with action buttons"""
    st.markdown('<h1 class="main-header">Remediation Approvals</h1>', unsafe_allow_html=True)
    st.markdown("Review and approve/reject proposed remediations")
    
    # Import approval manager (lazy import to avoid slow startup)
    try:
        import sys
        import importlib.util
        
        # Add project root to Python path (parent of ui directory)
        project_root = Path(__file__).parent.parent.resolve()
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        
        # Load manager.py directly to avoid relative import issues
        manager_path = project_root / "app" / "approval" / "manager.py"
        if not manager_path.exists():
            raise ImportError(f"Approval manager not found at {manager_path}")
        
        spec = importlib.util.spec_from_file_location("approval_manager_module", manager_path)
        manager_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(manager_module)
        
        get_approval_manager = manager_module.get_approval_manager
        ApprovalStatus = manager_module.ApprovalStatus
        approval_manager = get_approval_manager()
    except Exception as e:
        st.error(f"Approval system not available: {str(e)}")
        st.info("Make sure you're running from the project root directory and dependencies are installed.")
        import traceback
        with st.expander("Error Details"):
            st.code(traceback.format_exc())
        return
    
    # Tabs for different statuses
    tab1, tab2, tab3 = st.tabs(["Pending", "Approved", "Rejected"])
    
    with tab1:
        st.subheader("Pending Approvals")
        pending = approval_manager.list_pending()
        
        if not pending:
            st.info("No pending approvals at this time.")
        else:
            for request in pending:
                with st.expander(f"Incident {request.incident_id} - {request.risk_level.upper()} RISK", expanded=True):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown(f"**Root Cause:** {request.root_cause}")
                        st.markdown(f"**Proposed Action:** {request.remediation_action}")
                        st.markdown(f"**Risk Level:** {request.risk_level}")
                        st.markdown(f"**Created:** {request.created_at}")
                        
                        # Show remediation details
                        if request.remediation_plan:
                            with st.expander("View Remediation Details"):
                                st.json(request.remediation_plan)
                    
                    with col2:
                        st.markdown("### Actions")
                        
                        # Approval comment
                        comment = st.text_input(
                            "Comment (optional)",
                            key=f"comment_{request.incident_id}",
                            placeholder="Add approval comment..."
                        )
                        
                        col_approve, col_reject = st.columns(2)
                        
                        with col_approve:
                            if st.button("✓ Approve", key=f"approve_{request.incident_id}", type="primary"):
                                with st.spinner("Approving and executing remediation..."):
                                    try:
                                        # Approve the remediation
                                        approval_manager.approve(
                                            request.incident_id,
                                            "ui-user",
                                            comment if comment else None
                                        )
                                        st.success("✅ Remediation approved!")
                                        
                                        # Execute remediation (lazy import)
                                        execution_attempted = False
                                        try:
                                            import sys
                                            import importlib.util
                                            
                                            project_root = Path(__file__).parent.parent.resolve()
                                            if str(project_root) not in sys.path:
                                                sys.path.insert(0, str(project_root))
                                            
                                            # Load remediation_executor.py directly to avoid import conflicts
                                            executor_path = project_root / "app" / "tools" / "remediation_executor.py"
                                            if not executor_path.exists():
                                                raise ImportError(f"Remediation executor not found at {executor_path}")
                                            
                                            spec = importlib.util.spec_from_file_location("remediation_executor_module", executor_path)
                                            executor_module = importlib.util.module_from_spec(spec)
                                            spec.loader.exec_module(executor_module)
                                            
                                            RemediationExecutor = executor_module.RemediationExecutor
                                            executor = RemediationExecutor()
                                            execution_attempted = True
                                            
                                            st.info("🔧 Executing remediation...")
                                            success, message = executor.execute_remediation(
                                                request.incident_id,
                                                request.remediation_plan,
                                                request.alert_data
                                            )
                                            
                                            if success:
                                                st.success(f"✅ Remediation executed successfully: {message}")
                                                st.info("� Refreshing page in 2 seconds...")
                                                time.sleep(2)
                                                st.rerun()
                                            else:
                                                st.error(f"⚠️ Execution failed: {message}")
                                        except Exception as exec_error:
                                            if execution_attempted:
                                                st.error(f"❌ Execution error: {str(exec_error)}")
                                                import traceback
                                                with st.expander("📋 Full Error Details (Click to expand)"):
                                                    st.code(traceback.format_exc())
                                            else:
                                                st.warning(f"⚠️ Could not load executor: {str(exec_error)}")
                                                st.info("Manual execution required - run the command from the remediation plan")
                                        
                                    except Exception as e:
                                        st.error(f"Error: {str(e)}")
                        
                        with col_reject:
                            if st.button("✗ Reject", key=f"reject_{request.incident_id}"):
                                reason = st.text_input(
                                    "Rejection reason (required)",
                                    key=f"reason_{request.incident_id}"
                                )
                                if reason:
                                    try:
                                        approval_manager.reject(
                                            request.incident_id,
                                            "ui-user",
                                            reason
                                        )
                                        st.success("Remediation rejected")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error: {str(e)}")
                                else:
                                    st.warning("Please provide a rejection reason")
    
    with tab2:
        st.subheader("Approved Remediations")
        # Load all approvals and filter approved
        approvals_dir = Path("approvals")
        if approvals_dir.exists():
            approved = []
            for file in approvals_dir.glob("*.json"):
                with open(file) as f:
                    data = json.load(f)
                    if data.get("status") == "approved":
                        approved.append(data)
            
            if not approved:
                st.info("No approved remediations yet.")
            else:
                for item in sorted(approved, key=lambda x: x.get("approved_at", ""), reverse=True):
                    with st.expander(f"Incident {item['incident_id']}"):
                        st.markdown(f"**Root Cause:** {item['root_cause']}")
                        st.markdown(f"**Action:** {item['remediation_action']}")
                        st.markdown(f"**Approved By:** {item.get('approved_by', 'Unknown')}")
                        st.markdown(f"**Approved At:** {item.get('approved_at', 'Unknown')}")
                        if item.get('comment'):
                            st.markdown(f"**Comment:** {item['comment']}")
        else:
            st.info("No approvals directory found.")
    
    with tab3:
        st.subheader("Rejected Remediations")
        # Load all approvals and filter rejected
        approvals_dir = Path("approvals")
        if approvals_dir.exists():
            rejected = []
            for file in approvals_dir.glob("*.json"):
                with open(file) as f:
                    data = json.load(f)
                    if data.get("status") == "rejected":
                        rejected.append(data)
            
            if not rejected:
                st.info("No rejected remediations.")
            else:
                for item in sorted(rejected, key=lambda x: x.get("rejected_at", ""), reverse=True):
                    with st.expander(f"Incident {item['incident_id']}"):
                        st.markdown(f"**Root Cause:** {item['root_cause']}")
                        st.markdown(f"**Action:** {item['remediation_action']}")
                        st.markdown(f"**Rejected By:** {item.get('rejected_by', 'Unknown')}")
                        st.markdown(f"**Rejected At:** {item.get('rejected_at', 'Unknown')}")
                        if item.get('rejection_reason'):
                            st.markdown(f"**Reason:** {item['rejection_reason']}")
        else:
            st.info("No approvals directory found.")

def render_postmortems():
    """Render postmortems page"""
    st.markdown('<h1 class="main-header">Postmortems</h1>', unsafe_allow_html=True)
    
    postmortems = load_postmortems()
    
    if not postmortems:
        st.info("No postmortems available yet.")
        return
    
    # Sidebar filter
    selected_id = st.selectbox(
        "Select Incident",
        [pm['id'] for pm in postmortems],
        index=0
    )
    
    # Find selected postmortem
    selected = next((pm for pm in postmortems if pm['id'] == selected_id), None)
    
    if selected:
        st.markdown(f"### {selected['id']}")
        st.caption(f"Generated: {selected['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
        st.markdown("---")
        
        # Display postmortem content
        st.markdown(selected['content'])
        
        # Download button
        st.download_button(
            label="Download Postmortem",
            data=selected['content'],
            file_name=f"{selected['id']}.md",
            mime="text/markdown"
        )


def render_settings():
    """Render settings page"""
    st.markdown('<h1 class="main-header">Settings</h1>', unsafe_allow_html=True)
    
    st.subheader("Environment Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.text_input("OpenAI API Key", type="password", value="***")
        st.text_input("Prometheus URL", value=os.getenv("PROMETHEUS_URL", ""))
        st.text_input("Loki URL", value=os.getenv("LOKI_URL", ""))
    
    with col2:
        st.selectbox("Default Severity Level", ["critical", "warning", "info"])
        st.checkbox("Enable Auto-remediation", value=False)
        st.checkbox("Send Slack Notifications", value=False)
    
    st.markdown("---")
    
    st.subheader("Guardrails")
    
    guardrails_file = Path("app/policies/guardrails.yaml")
    if guardrails_file.exists():
        with open(guardrails_file, 'r') as f:
            content = f.read()
        
        st.code(content, language='yaml')
    
    st.markdown("---")
    
    if st.button("Save Configuration"):
        st.success("Settings saved successfully!")


def main():
    """Main application"""
    
    # Initialize session state
    if 'selected_incident' not in st.session_state:
        st.session_state['selected_incident'] = None
    
    # Render sidebar and get selected page
    page = render_sidebar()
    
    # Render selected page
    if page == "Dashboard":
        render_dashboard()
    elif page == "Submit Alert":
        render_submit_alert()
    elif page == "Incidents":
        render_incidents()
    elif page == "Approvals":
        render_approvals()
    elif page == "Postmortems":
        render_postmortems()
    elif page == "Settings":
        render_settings()


if __name__ == "__main__":
    main()
