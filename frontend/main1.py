import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import requests
import time

# Page configuration
st.set_page_config(
    page_title="CodeSentinel AI - Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for beautiful styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 30px;
        text-align: center;
    }
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .critical-alert {
        background: #fee;
        border-left: 4px solid #dc3545;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .warning-alert {
        background: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .success-alert {
        background: #d4edda;
        border-left: 4px solid #28a745;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .info-alert {
        background: #d1ecf1;
        border-left: 4px solid #17a2b8;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .agent-status {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 15px;
        font-size: 12px;
        font-weight: bold;
        margin: 2px;
    }
    .agent-active {
        background: #28a745;
        color: white;
    }
    .agent-idle {
        background: #6c757d;
        color: white;
    }
    .agent-error {
        background: #dc3545;
        color: white;
    }
    .loading-spinner {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 100px;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar Navigation
st.sidebar.markdown("### Navigation")
page = st.sidebar.selectbox(
    "Select Page",
    ["Dashboard", "PR Analysis", "Repository Manager", "Analytics", "Agent Configuration", "Settings"]
)

# Initialize session state
if 'analysis_history' not in st.session_state:
    st.session_state.analysis_history = []
if 'current_analysis' not in st.session_state:
    st.session_state.current_analysis = None
if 'backend_connected' not in st.session_state:
    st.session_state.backend_connected = False

# Backend API configuration
BACKEND_URL = "http://localhost:8000"  # Update with your backend URL

def check_backend_connection():
    """Check if backend is available"""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def call_backend_api(endpoint, data=None, method="GET"):
    """Make API call to backend"""
    try:
        url = f"{BACKEND_URL}{endpoint}"
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=30)
        
        if response.status_code == 200:
            return {"status": "success", "data": response.json()}
        else:
            return {"status": "error", "message": f"HTTP {response.status_code}"}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": str(e)}

# Main Dashboard Page
if page == "Dashboard":
    # Header
    st.markdown("""
        <div class="main-header">
            <h1 style="color: white; margin: 0;">CodeSentinel AI Dashboard</h1>
            <p style="color: white; margin: 10px 0 0 0;">Advanced Code Quality Guardian with AI Intelligence</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Backend Connection Status
    backend_status = check_backend_connection()
    st.session_state.backend_connected = backend_status
    
    if backend_status:
        st.success("Backend Connected")
    else:
        st.error("Backend Not Connected - Please start the backend server")
        st.info("Start backend: `uvicorn main:app --reload`")
    
    # System Status Overview
    if backend_status:
        with st.spinner("Loading system metrics..."):
            metrics_response = call_backend_api("/api/metrics")
            
            if metrics_response["status"] == "success":
                metrics = metrics_response["data"]
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total PRs", metrics.get("total_prs", 0))
                with col2:
                    st.metric("Critical Issues", metrics.get("critical_issues", 0))
                with col3:
                    st.metric("Issues Fixed", metrics.get("fixed_issues", 0))
                with col4:
                    st.metric("Avg Fix Time", metrics.get("avg_fix_time", "N/A"))
            else:
                st.warning("Unable to load system metrics")
    
    # Agent Status Section
    st.subheader("Agent Status")
    
    if backend_status:
        with st.spinner("Loading agent status..."):
            agent_response = call_backend_api("/api/agents/status")
            
            if agent_response["status"] == "success":
                agents = agent_response["data"]
                
                # Display agent status badges
                agent_status_html = ""
                for agent_name, agent_data in agents.items():
                    status = agent_data.get("status", "unknown")
                    status_class = f"agent-{status}"
                    agent_status_html += f'<span class="agent-status {status_class}">{agent_name.title()}: {status.title()}</span>'
                
                if agent_status_html:
                    st.markdown(agent_status_html, unsafe_allow_html=True)
                else:
                    st.info("No agents currently active")
            else:
                st.warning("Unable to load agent status")
    else:
        st.info("Connect to backend to view agent status")
    
    # Repository Status
    st.subheader("Connected Repositories")
    
    if backend_status:
        with st.spinner("Loading repositories..."):
            repo_response = call_backend_api("/api/repositories")
            
            if repo_response["status"] == "success":
                repositories = repo_response["data"]
                
                if repositories:
                    for repo in repositories:
                        col1, col2, col3 = st.columns([3, 1, 1])
                        
                        with col1:
                            st.write(f"**{repo.get('name', 'Unknown')}**")
                        with col2:
                            status = repo.get('status', 'unknown')
                            if status == 'active':
                                st.success(status.title())
                            elif status == 'error':
                                st.error(status.title())
                            else:
                                st.info(status.title())
                        with col3:
                            st.write(f"Issues: {repo.get('issues', 0)}")
                        
                        st.divider()
                else:
                    st.info("No repositories connected yet")
            else:
                st.warning("Unable to load repositories")
    else:
        st.info("Connect to backend to view repositories")

# PR Analysis Page
elif page == "PR Analysis":
    st.header("Pull Request Analysis")
    
    # PR Input Section
    col1, col2 = st.columns([3, 1])
    
    with col1:
        pr_url = st.text_input("GitHub PR URL", placeholder="https://github.com/owner/repo/pull/123")
    
    with col2:
        analysis_mode = st.selectbox("Analysis Mode", ["Full Analysis", "Security Only", "Quality Only"])
    
    if st.button("Analyze PR", type="primary"):
        if not pr_url:
            st.error("Please enter a valid PR URL")
        elif not st.session_state.backend_connected:
            st.error("Backend not connected. Please start the backend server.")
        else:
            with st.spinner("Analyzing PR... This may take a few minutes"):
                # Progress tracking
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Call backend API for PR analysis
                analysis_data = {
                    "pr_url": pr_url,
                    "analysis_mode": analysis_mode
                }
                
                status_text.text("Sending analysis request to backend...")
                progress_bar.progress(20)
                
                response = call_backend_api("/api/analysis/pr", analysis_data, "POST")
                
                if response["status"] == "success":
                    progress_bar.progress(100)
                    status_text.text("Analysis complete!")
                    
                    # Store results
                    st.session_state.current_analysis = response["data"]
                    st.session_state.analysis_history.append({
                        "pr_url": pr_url,
                        "timestamp": datetime.now(),
                        "analysis_mode": analysis_mode
                    })
                    
                    st.success("PR Analysis Complete!")
                else:
                    st.error(f"Analysis failed: {response['message']}")
    
    # Display Analysis Results
    if st.session_state.current_analysis:
        results = st.session_state.current_analysis
        
        st.subheader("Analysis Results")
        
        # Overall Status
        overall_status = results.get("overall_status", "unknown")
        if overall_status == "approved":
            st.success("APPROVED FOR MERGE")
        elif overall_status == "blocked":
            st.error("MERGE BLOCKED - Critical issues found")
        elif overall_status == "warning":
            st.warning("MERGE WITH CAUTION - Review issues carefully")
        else:
            st.info("Analysis completed - Review results below")
        
        # Security Findings
        if "security_findings" in results:
            st.subheader("Security Analysis")
            security_findings = results["security_findings"]
            
            if security_findings:
                for finding in security_findings:
                    severity = finding.get("severity", "unknown").lower()
                    with st.expander(f"{finding.get('type', 'Unknown')} - {finding.get('severity', 'Unknown')} Severity"):
                        st.write(f"**File:** {finding.get('file', 'Unknown')}")
                        st.write(f"**Line:** {finding.get('line', 'Unknown')}")
                        st.write(f"**Description:** {finding.get('description', 'No description')}")
                        
                        if severity == "critical":
                            st.error("This is a critical security vulnerability that must be fixed before merge.")
            else:
                st.success("No security issues found!")
        
        # Quality Issues
        if "quality_issues" in results:
            st.subheader("Code Quality Analysis")
            quality_issues = results["quality_issues"]
            
            if quality_issues:
                df = pd.DataFrame(quality_issues)
                st.dataframe(df, use_container_width=True)
            else:
                st.success("No quality issues found!")
        
        # Logic Issues
        if "logic_issues" in results:
            st.subheader("Logic Analysis")
            logic_issues = results["logic_issues"]
            
            if logic_issues:
                for issue in logic_issues:
                    with st.expander(f"{issue.get('type', 'Unknown')} - {issue.get('severity', 'Unknown')} Severity"):
                        st.write(f"**File:** {issue.get('file', 'Unknown')}")
                        st.write(f"**Line:** {issue.get('line', 'Unknown')}")
                        st.write(f"**Description:** {issue.get('description', 'No description')}")
            else:
                st.success("No logic issues found!")
        
        # Recommendations
        if "recommendations" in results:
            st.subheader("Recommendations")
            recommendations = results["recommendations"]
            
            for rec in recommendations:
                rec_type = rec.get("type", "info")
                message = rec.get("message", "No message")
                
                if rec_type == "critical":
                    st.error(message)
                elif rec_type == "warning":
                    st.warning(message)
                elif rec_type == "success":
                    st.success(message)
                else:
                    st.info(message)

# Repository Manager Page
elif page == "Repository Manager":
    st.header("Repository Manager")
    
    # Add Repository Section
    with st.expander("Add New Repository"):
        repo_url = st.text_input("Repository URL")
        webhook_secret = st.text_input("Webhook Secret", type="password")
        
        if st.button("Add Repository"):
            if not repo_url:
                st.error("Please enter a repository URL")
            elif not st.session_state.backend_connected:
                st.error("Backend not connected")
            else:
                add_repo_data = {
                    "repo_url": repo_url,
                    "webhook_secret": webhook_secret
                }
                
                response = call_backend_api("/api/repositories", add_repo_data, "POST")
                
                if response["status"] == "success":
                    st.success("Repository added successfully!")
                    st.rerun()
                else:
                    st.error(f"Failed to add repository: {response['message']}")
    
    # Repository List
    st.subheader("Connected Repositories")
    
    if st.session_state.backend_connected:
        response = call_backend_api("/api/repositories")
        
        if response["status"] == "success":
            repositories = response["data"]
            
            if repositories:
                for repo in repositories:
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                    
                    with col1:
                        st.write(f"**{repo.get('name', 'Unknown')}**")
                        st.write(f"Last scan: {repo.get('last_scan', 'Never')}")
                    
                    with col2:
                        status = repo.get('status', 'unknown')
                        if status == 'active':
                            st.success(status.title())
                        elif status == 'error':
                            st.error(status.title())
                        else:
                            st.info(status.title())
                    
                    with col3:
                        st.write(f"Issues: {repo.get('issues', 0)}")
                    
                    with col4:
                        if st.button(f"Remove", key=f"remove_{repo.get('id', 'unknown')}"):
                            # Call remove API
                            remove_response = call_backend_api(f"/api/repositories/{repo.get('id')}", method="DELETE")
                            if remove_response["status"] == "success":
                                st.success("Repository removed!")
                                st.rerun()
                            else:
                                st.error("Failed to remove repository")
                    
                    st.divider()
            else:
                st.info("No repositories connected yet. Add your first repository above.")
        else:
            st.error("Unable to load repositories")
    else:
        st.error("Backend not connected")

# Analytics Page
elif page == "Analytics":
    st.header("Analytics & Reporting")
    
    if not st.session_state.backend_connected:
        st.error("Backend not connected. Please start the backend server to view analytics.")
    else:
        # Time range selector
        time_range = st.selectbox("Time Range", ["Last 7 days", "Last 30 days", "Last 90 days", "All time"])
        
        with st.spinner("Loading analytics data..."):
            analytics_response = call_backend_api(f"/api/analytics?range={time_range}")
            
            if analytics_response["status"] == "success":
                analytics_data = analytics_response["data"]
                
                # Display analytics charts here
                st.subheader("Issue Trends")
                
                if "issue_trends" in analytics_data:
                    # Create charts from real data
                    st.info("Analytics data loaded successfully")
                else:
                    st.info("No analytics data available yet")
            else:
                st.error("Unable to load analytics data")

# Agent Configuration Page
elif page == "Agent Configuration":
    st.header("Agent Configuration")
    
    if not st.session_state.backend_connected:
        st.error("Backend not connected. Please start the backend server to configure agents.")
    else:
        with st.spinner("Loading agent configurations..."):
            config_response = call_backend_api("/api/agents/config")
            
            if config_response["status"] == "success":
                agent_configs = config_response["data"]
                
                for agent_name, config in agent_configs.items():
                    with st.expander(f"{agent_name.title()} Agent Configuration"):
                        # Configuration form for each agent
                        st.selectbox(f"Model", ["codellama:13b", "mistral:7b", "qwen-coder:7b"], key=f"model_{agent_name}")
                        st.slider(f"Sensitivity", 0.1, 1.0, 0.8, key=f"sensitivity_{agent_name}")
                        st.checkbox(f"Auto-fix enabled", key=f"autofix_{agent_name}")
                        
                        if st.button(f"Save {agent_name.title()} Config", key=f"save_{agent_name}"):
                            # Save configuration via API
                            save_config_data = {
                                "agent": agent_name,
                                "model": st.session_state[f"model_{agent_name}"],
                                "sensitivity": st.session_state[f"sensitivity_{agent_name}"],
                                "autofix": st.session_state[f"autofix_{agent_name}"]
                            }
                            
                            save_response = call_backend_api("/api/agents/config", save_config_data, "POST")
                            
                            if save_response["status"] == "success":
                                st.success(f"{agent_name.title()} configuration saved!")
                            else:
                                st.error("Failed to save configuration")
            else:
                st.error("Unable to load agent configurations")

# Settings Page
elif page == "Settings":
    st.header("System Settings")
    
    if not st.session_state.backend_connected:
        st.error("Backend not connected. Please start the backend server to access settings.")
    else:
        # GitHub Integration
        with st.expander("GitHub Integration"):
            github_token = st.text_input("GitHub Token", type="password")
            webhook_url = st.text_input("Webhook URL")
            auto_analysis = st.checkbox("Enable automatic PR analysis")
            
            if st.button("Save GitHub Settings"):
                settings_data = {
                    "github_token": github_token,
                    "webhook_url": webhook_url,
                    "auto_analysis": auto_analysis
                }
                
                response = call_backend_api("/api/settings/github", settings_data, "POST")
                
                if response["status"] == "success":
                    st.success("GitHub settings saved!")
                else:
                    st.error("Failed to save GitHub settings")
        
        # Notification Settings
        with st.expander("Notifications"):
            email_notifications = st.checkbox("Email notifications")
            slack_notifications = st.checkbox("Slack notifications")
            slack_webhook = st.text_input("Slack webhook URL")
            
            if st.button("Save Notification Settings"):
                notification_data = {
                    "email": email_notifications,
                    "slack": slack_notifications,
                    "slack_webhook": slack_webhook
                }
                
                response = call_backend_api("/api/settings/notifications", notification_data, "POST")
                
                if response["status"] == "success":
                    st.success("Notification settings saved!")
                else:
                    st.error("Failed to save notification settings")
        
        # Security Settings
        with st.expander("Security Settings"):
            require_auth = st.checkbox("Require authentication")
            auth_method = st.selectbox("Authentication method", ["GitHub OAuth", "LDAP", "Local"])
            audit_logging = st.checkbox("Enable audit logging")
            
            if st.button("Save Security Settings"):
                security_data = {
                    "require_auth": require_auth,
                    "auth_method": auth_method,
                    "audit_logging": audit_logging
                }
                
                response = call_backend_api("/api/settings/security", security_data, "POST")
                
                if response["status"] == "success":
                    st.success("Security settings saved!")
                else:
                    st.error("Failed to save security settings")

# Sidebar system info
with st.sidebar:
    st.markdown("---")
    st.markdown("### System Status")
    
    if st.session_state.backend_connected:
        st.success("Backend: Connected")
    else:
        st.error("Backend: Disconnected")
    
    # Backend URL configuration
    st.markdown("### Backend Configuration")
    new_backend_url = st.text_input("Backend URL", value=BACKEND_URL)
    
    if st.button("Test Connection"):
        try:
            response = requests.get(f"{new_backend_url}/health", timeout=5)
            if response.status_code == 200:
                st.success("Connection successful!")
                BACKEND_URL = new_backend_url
            else:
                st.error("Connection failed!")
        except:
            st.error("Connection failed!")
    
    if st.button("Refresh Dashboard"):
        st.rerun()

