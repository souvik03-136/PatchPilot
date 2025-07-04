import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import time
import json
import numpy as np
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
    .sidebar-section {
        margin-bottom: 30px;
        padding: 15px;
        background: #f8f9fa;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar Navigation
st.sidebar.markdown("### Navigation")
page = st.sidebar.selectbox(
    "Select Page",
    ["Dashboard", "PR Analysis", "Repository Manager", "Analytics", "Agent Configuration", "Settings"]
)

# Initialize session state for data persistence
if 'analysis_history' not in st.session_state:
    st.session_state.analysis_history = []
if 'current_analysis' not in st.session_state:
    st.session_state.current_analysis = None

# Mock data for demonstration
@st.cache_data
def get_mock_data():
    return {
        "repositories": [
            {"name": "frontend-app", "status": "active", "last_scan": "2 hours ago", "issues": 3},
            {"name": "backend-api", "status": "scanning", "last_scan": "scanning...", "issues": 0},
            {"name": "mobile-app", "status": "error", "last_scan": "1 day ago", "issues": 7}
        ],
        "agents": {
            "security": {"status": "active", "load": 78, "last_active": "1 min ago"},
            "quality": {"status": "active", "load": 45, "last_active": "30 sec ago"},
            "logic": {"status": "idle", "load": 12, "last_active": "5 min ago"},
            "context": {"status": "active", "load": 33, "last_active": "2 min ago"},
            "decision": {"status": "active", "load": 67, "last_active": "10 sec ago"}
        },
        "metrics": {
            "total_prs": 127,
            "critical_issues": 5,
            "fixed_issues": 89,
            "avg_fix_time": "2.3 hours"
        }
    }

# API connection function
def call_backend_api(endpoint, data=None):
    """Mock API call - replace with actual backend URL"""
    try:
        # Simulate API call
        time.sleep(1)  # Simulate network delay
        return {"status": "success", "data": get_mock_data()}
    except Exception as e:
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
    
    # System Status Overview
    col1, col2, col3, col4 = st.columns(4)
    data = get_mock_data()
    
    with col1:
        st.metric("Total PRs Analyzed", data["metrics"]["total_prs"], delta="12 today")
    with col2:
        st.metric("Critical Issues", data["metrics"]["critical_issues"], delta="-3 this week")
    with col3:
        st.metric("Issues Fixed", data["metrics"]["fixed_issues"], delta="23 today")
    with col4:
        st.metric("Avg Fix Time", data["metrics"]["avg_fix_time"], delta="-0.5 hours")
    
    # Agent Status Section
    st.subheader("Agent Status")
    agent_col1, agent_col2 = st.columns([2, 1])
    
    with agent_col1:
        agent_status_html = ""
        for agent_name, agent_data in data["agents"].items():
            status_class = f"agent-{agent_data['status']}"
            agent_status_html += f'<span class="agent-status {status_class}">{agent_name.title()}: {agent_data["status"].title()}</span>'
        
        st.markdown(agent_status_html, unsafe_allow_html=True)
        
        # Agent load chart
        agent_names = list(data["agents"].keys())
        agent_loads = [data["agents"][name]["load"] for name in agent_names]
        
        fig = px.bar(
            x=agent_names,
            y=agent_loads,
            title="Agent Workload Distribution",
            labels={"x": "Agent", "y": "Load (%)"},
            color=agent_loads,
            color_continuous_scale="viridis"
        )
        fig.update_layout(showlegend=False, height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    with agent_col2:
        st.subheader("Agent Details")
        for agent_name, agent_data in data["agents"].items():
            with st.expander(f"{agent_name.title()} Agent"):
                st.write(f"**Status:** {agent_data['status'].title()}")
                st.write(f"**Load:** {agent_data['load']}%")
                st.write(f"**Last Active:** {agent_data['last_active']}")
                st.progress(agent_data['load'] / 100)
    
    # Repository Status
    st.subheader("Repository Status")
    repo_df = pd.DataFrame(data["repositories"])
    
    # Color code based on status
    def get_status_color(status):
        colors = {"active": "#28a745", "scanning": "#ffc107", "error": "#dc3545"}
        return colors.get(status, "#6c757d")
    
    repo_df["status_color"] = repo_df["status"].apply(get_status_color)
    
    fig = px.scatter(
        repo_df,
        x="name",
        y="issues",
        size="issues",
        color="status",
        title="Repository Issues Overview",
        labels={"issues": "Number of Issues", "name": "Repository"},
        color_discrete_map={"active": "#28a745", "scanning": "#ffc107", "error": "#dc3545"}
    )
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
    
    # Recent Activity
    st.subheader("Recent Activity")
    recent_activities = [
        {"time": "2 minutes ago", "event": "Security scan completed for frontend-app", "type": "info"},
        {"time": "5 minutes ago", "event": "Critical vulnerability detected in backend-api", "type": "critical"},
        {"time": "10 minutes ago", "event": "Auto-fix applied to mobile-app", "type": "success"},
        {"time": "15 minutes ago", "event": "Quality check passed for frontend-app", "type": "success"}
    ]
    
    for activity in recent_activities:
        alert_class = f"{activity['type']}-alert"
        st.markdown(f'<div class="{alert_class}"><strong>{activity["time"]}</strong>: {activity["event"]}</div>', 
                   unsafe_allow_html=True)

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
        if pr_url:
            with st.spinner("Analyzing PR... This may take a few minutes"):
                # Progress tracking
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Simulate analysis stages
                stages = [
                    ("Fetching PR data", 20),
                    ("Running security scan", 40),
                    ("Analyzing code quality", 60),
                    ("Checking logic patterns", 80),
                    ("Generating recommendations", 100)
                ]
                
                for stage, progress in stages:
                    status_text.text(f"Status: {stage}...")
                    progress_bar.progress(progress)
                    time.sleep(1)
                
                # Mock analysis results
                analysis_results = {
                    "pr_info": {
                        "title": "Add user authentication module",
                        "author": "john.doe",
                        "files_changed": 8,
                        "lines_added": 234,
                        "lines_removed": 12
                    },
                    "security_findings": [
                        {"type": "SQL Injection", "severity": "Critical", "file": "auth.py", "line": 45, "description": "User input not sanitized"},
                        {"type": "Weak Password", "severity": "Medium", "file": "validators.py", "line": 12, "description": "Password requirements too weak"}
                    ],
                    "quality_issues": [
                        {"type": "Complexity", "severity": "High", "file": "auth.py", "line": 78, "description": "Function too complex (CC: 15)"},
                        {"type": "Documentation", "severity": "Medium", "file": "models.py", "line": 1, "description": "Missing docstring"}
                    ],
                    "logic_issues": [
                        {"type": "Null Pointer", "severity": "High", "file": "utils.py", "line": 23, "description": "Potential null reference"}
                    ],
                    "overall_score": 6.5,
                    "recommendation": "Fix critical security issues before merge"
                }
                
                # Store in session state
                st.session_state.current_analysis = analysis_results
                st.session_state.analysis_history.append({
                    "pr_url": pr_url,
                    "timestamp": datetime.now(),
                    "score": analysis_results["overall_score"]
                })
                
                status_text.text("Analysis complete!")
                st.success("PR Analysis Complete!")
    
    # Display Analysis Results
    if st.session_state.current_analysis:
        results = st.session_state.current_analysis
        
        # PR Overview
        st.subheader("PR Overview")
        pr_col1, pr_col2, pr_col3, pr_col4 = st.columns(4)
        
        with pr_col1:
            st.metric("Files Changed", results["pr_info"]["files_changed"])
        with pr_col2:
            st.metric("Lines Added", results["pr_info"]["lines_added"])
        with pr_col3:
            st.metric("Lines Removed", results["pr_info"]["lines_removed"])
        with pr_col4:
            st.metric("Overall Score", f"{results['overall_score']}/10")
        
        # Security Findings
        st.subheader("Security Analysis")
        if results["security_findings"]:
            for finding in results["security_findings"]:
                severity_color = {"Critical": "error", "High": "warning", "Medium": "info", "Low": "success"}
                with st.expander(f"{finding['type']} - {finding['severity']} Severity"):
                    st.write(f"**File:** {finding['file']}")
                    st.write(f"**Line:** {finding['line']}")
                    st.write(f"**Description:** {finding['description']}")
                    if finding['severity'] == 'Critical':
                        st.error("This is a critical security vulnerability that must be fixed before merge.")
        else:
            st.success("No security issues found!")
        
        # Quality Issues
        st.subheader("Code Quality Analysis")
        if results["quality_issues"]:
            quality_df = pd.DataFrame(results["quality_issues"])
            st.dataframe(quality_df, use_container_width=True)
        else:
            st.success("No quality issues found!")
        
        # Logic Issues
        st.subheader("Logic Analysis")
        if results["logic_issues"]:
            for issue in results["logic_issues"]:
                with st.expander(f"{issue['type']} - {issue['severity']} Severity"):
                    st.write(f"**File:** {issue['file']}")
                    st.write(f"**Line:** {issue['line']}")
                    st.write(f"**Description:** {issue['description']}")
        else:
            st.success("No logic issues found!")
        
        # Recommendation
        st.subheader("Recommendation")
        if results["overall_score"] < 7:
            st.error(f"Recommendation: {results['recommendation']}")
            st.error("MERGE BLOCKED - Critical issues must be resolved")
        elif results["overall_score"] < 8:
            st.warning(f"Recommendation: {results['recommendation']}")
            st.warning("MERGE WITH CAUTION - Review issues carefully")
        else:
            st.success("APPROVED FOR MERGE - No critical issues found")

# Repository Manager Page
elif page == "Repository Manager":
    st.header("Repository Manager")
    
    # Add Repository Section
    with st.expander("Add New Repository"):
        repo_url = st.text_input("Repository URL")
        webhook_secret = st.text_input("Webhook Secret", type="password")
        if st.button("Add Repository"):
            st.success(f"Repository {repo_url} added successfully!")
    
    # Repository List
    st.subheader("Connected Repositories")
    repos = get_mock_data()["repositories"]
    
    for repo in repos:
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            
            with col1:
                st.write(f"**{repo['name']}**")
                st.write(f"Last scan: {repo['last_scan']}")
            
            with col2:
                status_colors = {"active": "🟢", "scanning": "🟡", "error": "🔴"}
                st.write(f"{status_colors.get(repo['status'], '⚪')} {repo['status'].title()}")
            
            with col3:
                st.write(f"Issues: {repo['issues']}")
            
            with col4:
                if st.button(f"Configure", key=f"config_{repo['name']}"):
                    st.info(f"Configuration for {repo['name']}")
            
            st.divider()

# Analytics Page
elif page == "Analytics":
    st.header("Analytics & Reporting")
    
    # Time range selector
    time_range = st.selectbox("Time Range", ["Last 7 days", "Last 30 days", "Last 90 days", "All time"])
    
    # Generate sample data for charts
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
    issues_data = pd.DataFrame({
        'date': dates,
        'critical': np.random.poisson(2, len(dates)),
        'high': np.random.poisson(5, len(dates)),
        'medium': np.random.poisson(10, len(dates)),
        'low': np.random.poisson(15, len(dates))
    })
    
    # Issues over time
    fig = px.line(
        issues_data.tail(30),
        x='date',
        y=['critical', 'high', 'medium', 'low'],
        title="Security Issues Over Time",
        labels={'value': 'Number of Issues', 'date': 'Date'}
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Issue distribution
    col1, col2 = st.columns(2)
    
    with col1:
        issue_types = ['SQL Injection', 'XSS', 'CSRF', 'Authentication', 'Authorization']
        issue_counts = [23, 18, 12, 8, 5]
        
        fig = px.pie(
            values=issue_counts,
            names=issue_types,
            title="Issue Types Distribution"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        severity_data = pd.DataFrame({
            'Severity': ['Critical', 'High', 'Medium', 'Low'],
            'Count': [5, 15, 25, 35],
            'Fixed': [2, 12, 20, 30]
        })
        
        fig = px.bar(
            severity_data,
            x='Severity',
            y=['Count', 'Fixed'],
            title="Issues by Severity",
            barmode='group'
        )
        st.plotly_chart(fig, use_container_width=True)

# Agent Configuration Page
elif page == "Agent Configuration":
    st.header("Agent Configuration")
    
    # Agent settings
    agents = get_mock_data()["agents"]
    
    for agent_name, agent_data in agents.items():
        with st.expander(f"{agent_name.title()} Agent Configuration"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.selectbox(f"Model", ["codellama:13b", "mistral:7b", "qwen-coder:7b"], key=f"model_{agent_name}")
                st.slider(f"Sensitivity", 0.1, 1.0, 0.8, key=f"sensitivity_{agent_name}")
            
            with col2:
                st.checkbox(f"Auto-fix enabled", key=f"autofix_{agent_name}")
                st.selectbox(f"Priority", ["High", "Medium", "Low"], key=f"priority_{agent_name}")
            
            if st.button(f"Save {agent_name.title()} Config", key=f"save_{agent_name}"):
                st.success(f"{agent_name.title()} configuration saved!")

# Settings Page
elif page == "Settings":
    st.header("System Settings")
    
    # GitHub Integration
    with st.expander("GitHub Integration"):
        st.text_input("GitHub Token", type="password")
        st.text_input("Webhook URL")
        st.checkbox("Enable automatic PR analysis")
    
    # Notification Settings
    with st.expander("Notifications"):
        st.checkbox("Email notifications")
        st.checkbox("Slack notifications")
        st.text_input("Slack webhook URL")
    
    # Security Settings
    with st.expander("Security Settings"):
        st.checkbox("Require authentication")
        st.selectbox("Authentication method", ["GitHub OAuth", "LDAP", "Local"])
        st.checkbox("Enable audit logging")
    
    if st.button("Save Settings"):
        st.success("Settings saved successfully!")

# Sidebar additional info
with st.sidebar:
    st.markdown("---")
    st.markdown("### System Info")
    st.write("**Version:** 1.0.0")
    st.write("**Status:** Online")
    st.write("**Uptime:** 99.9%")
    
    st.markdown("### Quick Stats")
    st.write("**PRs Today:** 12")
    st.write("**Issues Found:** 8")
    st.write("**Auto-Fixed:** 5")
    
    if st.button("Emergency Stop"):
        st.error("All agents stopped!")
    
    if st.button("Refresh Data"):
        st.cache_data.clear()
        st.rerun()

