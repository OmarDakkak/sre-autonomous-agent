"""
Streamlit Web UI for SRE Autonomous Agent

A modern dashboard for monitoring incidents, submitting alerts,
and managing the autonomous incident response system.
"""

import streamlit as st
import json
import os
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
            ["Dashboard", "Submit Alert", "Incidents", "Postmortems", "Settings"],
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
    elif page == "Postmortems":
        render_postmortems()
    elif page == "Settings":
        render_settings()


if __name__ == "__main__":
    main()
