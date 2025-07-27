import streamlit as st
import requests
import json
import time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io
import base64

# Page configuration
st.set_page_config(
    page_title="PatchPilot",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 0.5rem;
        text-align: center;
    }
    
    .sub-header {
        font-size: 1.2rem;
        color: #6b7280;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 1rem;
        color: white;
        margin: 0.5rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .status-card {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 4px solid #10b981;
    }
    
    .error-card {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 4px solid #ef4444;
        background-color: #fef2f2;
    }
    
    .warning-card {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 4px solid #f59e0b;
        background-color: #fffbeb;
    }
    
    .info-card {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 4px solid #3b82f6;
        background-color: #eff6ff;
    }
    
    .analysis-result {
        padding: 1.5rem;
        border-radius: 1rem;
        margin: 1rem 0;
        background: white;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        border: 1px solid #e5e7eb;
    }
    
    .severity-critical {
        color: #dc2626;
        font-weight: bold;
    }
    
    .severity-high {
        color: #ea580c;
        font-weight: bold;
    }
    
    .severity-medium {
        color: #d97706;
        font-weight: bold;
    }
    
    .severity-low {
        color: #059669;
        font-weight: bold;
    }
    
    .decision-approve {
        background: linear-gradient(135deg, #10b981, #059669);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        display: inline-block;
        margin: 0.5rem 0;
    }
    
    .decision-changes {
        background: linear-gradient(135deg, #f59e0b, #d97706);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        display: inline-block;
        margin: 0.5rem 0;
    }
    
    .decision-block {
        background: linear-gradient(135deg, #ef4444, #dc2626);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        display: inline-block;
        margin: 0.5rem 0;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 0.5rem 1.5rem;
        border-radius: 0.5rem;
        background-color: transparent;
        border: 2px solid transparent;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
    }
    
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #f8fafc, #e2e8f0);
        border: 1px solid #cbd5e1;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'backend_url' not in st.session_state:
    st.session_state.backend_url = "http://localhost:8000"
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = {}
if 'task_ids' not in st.session_state:
    st.session_state.task_ids = {}

# Helper functions
def make_request(endpoint, method='GET', data=None):
    """Make API request to backend"""
    try:
        url = f"{st.session_state.backend_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        if method == 'GET':
            response = requests.get(url, timeout=10)
        elif method == 'POST':
            response = requests.post(url, json=data, timeout=30)
        elif method == 'DELETE':
            response = requests.delete(url, timeout=10)
        
        if response.status_code in [200, 201, 202]:
            return response.json(), None
        else:
            return None, f"Error {response.status_code}: {response.text}"
    except requests.exceptions.RequestException as e:
        return None, f"Connection error: {str(e)}"

def format_decision_clean(decision):
    """Format decision with clean emoji display"""
    decision_text = decision.get('decision', 'UNKNOWN')
    
    decision_emojis = {
        'APPROVE': '✅',
        'REQUEST_CHANGES': '⚠️',
        'MANUAL_REVIEW': '⚠️',
        'BLOCK': '🚫'
    }
    
    emoji = decision_emojis.get(decision_text, '❓')
    return f"{emoji} {decision_text}"

def get_decision_color(decision_text):
    """Get color for decision badge"""
    colors = {
        'APPROVE': 'success',
        'REQUEST_CHANGES': 'warning', 
        'MANUAL_REVIEW': 'warning',
        'BLOCK': 'error'
    }
    return colors.get(decision_text, 'info')

def poll_task_status(task_id, task_type="analysis"):
    """Poll task status until completion"""
    placeholder = st.empty()
    progress_bar = st.progress(0)
    
    max_attempts = 120  # 2 minutes max
    attempt = 0
    
    while attempt < max_attempts:
        result, error = make_request(f"api/analysis/status/{task_id}")
        
        if error:
            placeholder.error(f"Error checking status: {error}")
            return None
        
        status = result.get('status', 'unknown')
        progress = min((attempt + 1) / max_attempts, 0.95)
        progress_bar.progress(progress)
        
        if status == 'completed':
            progress_bar.progress(1.0)
            placeholder.success("✅ Analysis completed!")
            return result
        elif status == 'error':
            placeholder.error(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")
            return None
        elif status in ['processing', 'queued']:
            placeholder.info(f"🔄 Status: {status.title()}...")
        
        time.sleep(1)
        attempt += 1
    
    placeholder.warning("⏰ Analysis is taking longer than expected. Check back later.")
    return None

# Sidebar
with st.sidebar:
    st.markdown("# 🚀 PatchPilot")
    st.markdown("*AI-Powered Code Analysis*")
    
    # Backend connection test
    st.markdown("### 🔗 Backend Connection")
    backend_url = st.text_input("Backend URL", value=st.session_state.backend_url)
    
    if st.button("Test Connection", type="primary"):
        st.session_state.backend_url = backend_url
        result, error = make_request("health")
        if error:
            st.error(f"❌ Connection failed: {error}")
        else:
            st.success("✅ Connected successfully!")
            st.json(result)

# Main app
st.markdown('<h1 class="main-header">🚀 PatchPilot</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">AI-Powered Code Review & Security Analysis Platform</p>', unsafe_allow_html=True)

# Navigation tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "🔍 PR Analysis", "💻 Code Analysis", "⚙️ Settings", "📈 Analytics"])

# Dashboard Tab
with tab1:
    st.markdown("## 📊 System Overview")
    
    # Get system metrics
    metrics_data, metrics_error = make_request("api/metrics")
    
    if metrics_error:
        st.error(f"Failed to load metrics: {metrics_error}")
    else:
        # System metrics in columns
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            cpu_percent = metrics_data.get('system', {}).get('cpu', 0)
            st.metric("CPU Usage", f"{cpu_percent:.1f}%", delta=None)
            
        with col2:
            memory_percent = metrics_data.get('system', {}).get('memory', {}).get('percent', 0)
            st.metric("Memory Usage", f"{memory_percent:.1f}%", delta=None)
            
        with col3:
            active_tasks = metrics_data.get('application', {}).get('active_tasks', 0)
            st.metric("Active Tasks", str(active_tasks), delta=None)
            
        with col4:
            queue_size = metrics_data.get('application', {}).get('queue_size', 0)
            st.metric("Queue Size", str(queue_size), delta=None)
    
    st.markdown("---")
    
    # Agent status
    agent_status, agent_error = make_request("api/agents/status")
    
    if agent_error:
        st.warning(f"Agent status unavailable: {agent_error}")
    else:
        st.markdown("### 🤖 Agent Status")
        
        if agent_status.get('status') == 'available':
            agents = agent_status.get('agents', {})
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Active Agents")
                for agent_name, agent_info in agents.items():
                    status_icon = "🟢" if agent_info['status'] == 'active' else "🔴"
                    st.markdown(f"{status_icon} **{agent_name.title()}** - {agent_info['model']}")
            
            with col2:
                st.markdown("#### Agent Statistics")
                total_agents = agent_status.get('total_agents', 0)
                active_agents = agent_status.get('active_agents', 0)
                st.metric("Total Agents", str(total_agents))
                st.metric("Active Agents", str(active_agents))
        else:
            st.error("Agent system is not available")

# PR Analysis Tab
with tab2:
    st.markdown("## 🔍 Pull Request Analysis")
    
    pr_url = st.text_input(
        "GitHub PR URL",
        placeholder="https://github.com/owner/repo/pull/123",
        help="Enter the full GitHub pull request URL"
    )
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        analysis_mode = st.selectbox(
            "Analysis Mode",
            ["standard", "deep", "security-focused"],
            help="Choose the depth of analysis"
        )
    
    with col2:
        if st.button("🚀 Start Analysis", type="primary", disabled=not pr_url):
            if pr_url:
                data = {
                    "pr_url": pr_url,
                    "analysis_mode": analysis_mode
                }
                
                result, error = make_request("api/analysis/pr", method="POST", data=data)
                
                if error:
                    st.error(f"Failed to start analysis: {error}")
                else:
                    task_id = result.get('task_id')
                    st.session_state.task_ids['pr'] = task_id
                    st.success(f"Analysis started! Task ID: {task_id}")
                    
                    # Poll for results
                    analysis_result = poll_task_status(task_id)
                    
                    if analysis_result and analysis_result.get('results'):
                        st.session_state.analysis_results['pr'] = analysis_result
    
    # Display PR analysis results
    if 'pr' in st.session_state.analysis_results:
        result = st.session_state.analysis_results['pr']
        results_data = result.get('results', {})
        
        if 'error' not in results_data:
            st.markdown("### 📊 Analysis Results")
            
            # Decision summary
            decision = results_data.get('decision', {})
            st.markdown("#### 🎯 Decision")
            
            decision_text = decision.get('decision', 'UNKNOWN')
            decision_color = get_decision_color(decision_text)
            
            # Use Streamlit's built-in status display
            if decision_color == 'success':
                st.success(format_decision_clean(decision))
            elif decision_color == 'warning':
                st.warning(format_decision_clean(decision))
            elif decision_color == 'error':
                st.error(format_decision_clean(decision))
            else:
                st.info(format_decision_clean(decision))
                
            st.markdown(f"**Summary:** {decision.get('summary', 'No summary available')}")
            
            # Issue breakdown
            security_issues = results_data.get('security_issues', [])
            quality_issues = results_data.get('quality_issues', [])
            logic_issues = results_data.get('logic_issues', [])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🔒 Security Issues", len(security_issues))
            with col2:
                st.metric("💎 Quality Issues", len(quality_issues))
            with col3:
                st.metric("🧠 Logic Issues", len(logic_issues))
            
            # Detailed issues
            if security_issues:
                st.markdown("#### 🔒 Security Issues")
                for issue in security_issues:
                    # Clean severity display without HTML tags
                    severity = issue.get('severity', 'unknown').upper()
                    severity_emoji = {
                        'CRITICAL': '🔴',
                        'HIGH': '🟠', 
                        'MEDIUM': '🟡',
                        'LOW': '🟢'
                    }.get(severity, '⚪')
                    
                    issue_type = issue.get('type', 'Unknown')
                    
                    with st.expander(f"{severity_emoji} {severity} - {issue_type}", expanded=False):
                        st.markdown(f"**Description:** {issue.get('description', 'No description')}")
                        st.markdown(f"**File:** `{issue.get('file', 'Unknown')}`")
                        if issue.get('line'):
                            st.markdown(f"**Line:** {issue.get('line')}")
                        if issue.get('code_snippet'):
                            st.code(issue.get('code_snippet'), language='python')
            
            if quality_issues:
                st.markdown("#### 💎 Quality Issues")
                for issue in quality_issues:
                    # Clean severity display without HTML tags
                    severity = issue.get('severity', 'unknown').upper()
                    severity_emoji = {
                        'CRITICAL': '🔴',
                        'HIGH': '🟠', 
                        'MEDIUM': '🟡',
                        'LOW': '🟢'
                    }.get(severity, '⚪')
                    
                    issue_type = issue.get('type', 'Unknown')
                    
                    with st.expander(f"{severity_emoji} {severity} - {issue_type}", expanded=False):
                        st.markdown(f"**Description:** {issue.get('description', 'No description')}")
                        st.markdown(f"**File:** `{issue.get('file', 'Unknown')}`")
                        if issue.get('line'):
                            st.markdown(f"**Line:** {issue.get('line')}")
            
            if logic_issues:
                st.markdown("#### 🧠 Logic Issues")
                for issue in logic_issues:
                    with st.expander(f"Logic Issue - {issue.get('type', 'Unknown')}", expanded=False):
                        st.markdown(f"**Description:** {issue.get('description', 'No description')}")
                        if issue.get('suggestions'):
                            st.markdown("**Suggestions:**")
                            for suggestion in issue['suggestions']:
                                st.markdown(f"- {suggestion}")
        else:
            st.error(f"Analysis failed: {results_data.get('error')}")

# Code Analysis Tab
with tab3:
    st.markdown("## 💻 Code Analysis")
    
    # Input method selection
    input_method = st.radio(
        "Choose input method:",
        ["📝 Paste Code", "📁 Upload File"],
        horizontal=True
    )
    
    code_snippets = []
    
    if input_method == "📝 Paste Code":
        col1, col2 = st.columns([3, 1])
        
        with col1:
            file_path = st.text_input("File Path", placeholder="e.g., src/auth.py")
        
        with col2:
            language = st.selectbox(
                "Language",
                ["python", "javascript", "java", "cpp", "go", "rust", "typescript", "php"],
                index=0
            )
        
        code_content = st.text_area(
            "Code Content",
            height=300,
            placeholder="Paste your code here..."
        )
        
        if file_path and code_content:
            code_snippets = [{
                "file_path": file_path,
                "content": code_content,
                "language": language
            }]
    
    elif input_method == "📁 Upload File":
        uploaded_files = st.file_uploader(
            "Choose files",
            accept_multiple_files=True,
            type=['py', 'js', 'java', 'cpp', 'go', 'rs', 'ts', 'php', 'txt']
        )
        
        if uploaded_files:
            for uploaded_file in uploaded_files:
                try:
                    content = uploaded_file.read().decode('utf-8')
                    file_extension = uploaded_file.name.split('.')[-1]
                    
                    # Map file extensions to languages
                    extension_map = {
                        'py': 'python', 'js': 'javascript', 'java': 'java',
                        'cpp': 'cpp', 'go': 'go', 'rs': 'rust',
                        'ts': 'typescript', 'php': 'php'
                    }
                    
                    language = extension_map.get(file_extension, 'unknown')
                    
                    code_snippets.append({
                        "file_path": uploaded_file.name,
                        "content": content,
                        "language": language
                    })
                except Exception as e:
                    st.error(f"Error reading {uploaded_file.name}: {str(e)}")
    
    # Analysis button
    if code_snippets:
        st.markdown(f"**Files ready for analysis:** {len(code_snippets)}")
        
        if st.button("🔍 Analyze Code", type="primary"):
            data = {"code_snippets": code_snippets}
            
            result, error = make_request("api/analysis/security", method="POST", data=data)
            
            if error:
                st.error(f"Failed to start analysis: {error}")
            else:
                task_id = result.get('task_id')
                st.session_state.task_ids['code'] = task_id
                st.success(f"Analysis started! Task ID: {task_id}")
                
                # Poll for results
                analysis_result = poll_task_status(task_id)
                
                if analysis_result and analysis_result.get('results'):
                    st.session_state.analysis_results['code'] = analysis_result
    
    # Display code analysis results
    if 'code' in st.session_state.analysis_results:
        result = st.session_state.analysis_results['code']
        results_data = result.get('results', {})
        
        if 'error' not in results_data:
            st.markdown("### 📊 Analysis Results")
            
            # Decision summary
            decision = results_data.get('decision', {})
            st.markdown("#### 🎯 Security Assessment")
            
            decision_text = decision.get('decision', 'UNKNOWN')
            decision_color = get_decision_color(decision_text)
            
            # Use Streamlit's built-in status display
            if decision_color == 'success':
                st.success(format_decision_clean(decision))
            elif decision_color == 'warning':
                st.warning(format_decision_clean(decision))
            elif decision_color == 'error':
                st.error(format_decision_clean(decision))
            else:
                st.info(format_decision_clean(decision))
                
            st.markdown(f"**Summary:** {decision.get('summary', 'No summary available')}")
            
            # Issue statistics
            severity_breakdown = results_data.get('severity_breakdown', {})
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("🔴 Critical", severity_breakdown.get('critical', 0))
            with col2:
                st.metric("🟠 High", severity_breakdown.get('high', 0))
            with col3:
                st.metric("🟡 Medium", severity_breakdown.get('medium', 0))
            with col4:
                st.metric("🟢 Low", severity_breakdown.get('low', 0))
            
            # Detailed issues
            security_issues = results_data.get('security_issues', [])
            
            if security_issues:
                st.markdown("#### 🔒 Security Issues Found")
                
                for i, issue in enumerate(security_issues):
                    # Clean severity display without HTML tags
                    severity = issue.get('severity', 'unknown').upper()
                    severity_emoji = {
                        'CRITICAL': '🔴',
                        'HIGH': '🟠', 
                        'MEDIUM': '🟡',
                        'LOW': '🟢'
                    }.get(severity, '⚪')
                    
                    issue_type = issue.get('type', 'Security Issue')
                    
                    with st.expander(
                        f"{severity_emoji} {severity} - {issue_type}",
                        expanded=i < 3  # Expand first 3 issues
                    ):
                        st.markdown(f"**Description:** {issue.get('description', 'No description')}")
                        st.markdown(f"**File:** `{issue.get('file', 'Unknown')}`")
                        
                        if issue.get('line'):
                            st.markdown(f"**Line:** {issue.get('line')}")
                        
                        if issue.get('confidence'):
                            confidence = issue.get('confidence') * 100
                            st.markdown(f"**Confidence:** {confidence:.1f}%")
                        
                        if issue.get('code_snippet'):
                            st.markdown("**Code:**")
                            st.code(issue.get('code_snippet'), language='python')
            else:
                st.success("🎉 No security issues found!")
        else:
            st.error(f"Analysis failed: {results_data.get('error')}")

# Settings Tab
with tab4:
    st.markdown("## ⚙️ Settings")
    
    # Agent Configuration
    st.markdown("### 🤖 Agent Configuration")
    
    config_data, config_error = make_request("api/agents/config")
    
    if config_error:
        st.error(f"Failed to load configuration: {config_error}")
    else:
        configs = config_data.get('configs', {})
        
        # Create form for agent settings
        with st.form("agent_config_form"):
            st.markdown("#### Model Settings")
            
            updated_configs = {}
            
            for agent_name, config in configs.items():
                st.markdown(f"**{agent_name.title()} Agent**")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    provider = st.selectbox(
                        f"Provider ({agent_name})",
                        ["gemini", "openai", "groq", "anthropic"],
                        index=["gemini", "openai", "groq", "anthropic"].index(config.get('provider', 'gemini')),
                        key=f"{agent_name}_provider"
                    )
                
                with col2:
                    # Model options based on provider
                    model_options = {
                        "gemini": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro"],
                        "openai": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
                        "groq": ["llama3-70b-8192", "llama3-8b-8192", "mixtral-8x7b-32768"],
                        "anthropic": ["claude-3-sonnet", "claude-3-haiku", "claude-3-opus"]
                    }
                    
                    current_model = config.get('model', 'gemini-1.5-flash')
                    available_models = model_options.get(provider, [current_model])
                    
                    if current_model not in available_models:
                        available_models.append(current_model)
                    
                    model = st.selectbox(
                        f"Model ({agent_name})",
                        available_models,
                        index=available_models.index(current_model) if current_model in available_models else 0,
                        key=f"{agent_name}_model"
                    )
                
                with col3:
                    temperature = st.slider(
                        f"Temperature ({agent_name})",
                        min_value=0.0,
                        max_value=1.0,
                        value=config.get('temperature', 0.3),
                        step=0.1,
                        key=f"{agent_name}_temperature"
                    )
                
                updated_configs[agent_name] = {
                    "provider": provider,
                    "model": model,
                    "temperature": temperature
                }
                
                st.markdown("---")
            
            if st.form_submit_button("💾 Save Configuration", type="primary"):
                result, error = make_request("api/agents/config", method="POST", data=updated_configs)
                
                if error:
                    st.error(f"Failed to update configuration: {error}")
                else:
                    st.success("✅ Configuration updated successfully!")
                    st.rerun()
    
    st.markdown("---")
    
    # Backend URL Configuration
    st.markdown("### 🔗 Backend Configuration")
    
    with st.form("backend_config_form"):
        new_backend_url = st.text_input(
            "Backend URL",
            value=st.session_state.backend_url,
            help="URL of the PatchPilot backend server"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.form_submit_button("💾 Save URL", type="primary"):
                st.session_state.backend_url = new_backend_url
                st.success("✅ Backend URL updated!")
        
        with col2:
            if st.form_submit_button("🧪 Test Connection"):
                result, error = make_request("health")
                if error:
                    st.error(f"❌ Connection failed: {error}")
                else:
                    st.success("✅ Connection successful!")

# Analytics Tab
with tab5:
    st.markdown("## 📈 Analytics")
    
    # Time range selector
    time_range = st.selectbox(
        "Time Range",
        ["24h", "7d", "30d"],
        index=1,
        help="Select the time range for analytics data"
    )
    
    # Get analytics data
    analytics_data, analytics_error = make_request(f"api/analytics?range={time_range}")
    
    if analytics_error:
        st.error(f"Failed to load analytics: {analytics_error}")
    else:
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Analyses",
                analytics_data.get('analysis_count', 0),
                help="Total number of analyses completed"
            )
        
        with col2:
            success_rate = analytics_data.get('success_rate', 0)
            st.metric(
                "Success Rate",
                f"{success_rate}%",
                help="Percentage of successful analyses"
            )
        
        with col3:
            avg_duration = analytics_data.get('avg_duration', 0)
            st.metric(
                "Avg Duration",
                f"{avg_duration:.1f}s",
                help="Average analysis duration"
            )
        
        with col4:
            total_issues = analytics_data.get('total_issues', 0)
            st.metric(
                "Issues Found",
                total_issues,
                help="Total number of issues detected"
            )
        
        st.markdown("---")
        
        # Issue breakdown chart
        issue_types = analytics_data.get('issue_types', {})
        
        if any(issue_types.values()):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 🔍 Issue Types Distribution")
                
                # Pie chart for issue types
                labels = [k.title() for k in issue_types.keys()]
                values = list(issue_types.values())
                
                fig_pie = go.Figure(data=[go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.3,
                    marker_colors=['#ef4444', '#f59e0b', '#10b981']
                )])
                
                fig_pie.update_layout(
                    showlegend=True,
                    height=400,
                    margin=dict(t=0, b=0, l=0, r=0)
                )
                
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col2:
                st.markdown("### 📊 Issue Summary")
                
                # Bar chart for issue counts
                fig_bar = px.bar(
                    x=labels,
                    y=values,
                    title="Issues by Type",
                    color=values,
                    color_continuous_scale="viridis"
                )
                
                fig_bar.update_layout(
                    showlegend=False,
                    height=400,
                    xaxis_title="Issue Type",
                    yaxis_title="Count"
                )
                
                st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("📊 No analysis data available for the selected time range.")
        
        st.markdown("---")
        
        # Analysis timeline (mock data for demonstration)
        st.markdown("### ⏱️ Analysis Timeline")
        
        # Create sample timeline data
        dates = pd.date_range(
            start=datetime.now() - timedelta(days=7),
            end=datetime.now(),
            periods=7
        )
        
        # Generate sample data based on actual metrics
        timeline_data = pd.DataFrame({
            'Date': dates,
            'Analyses': [max(1, analytics_data.get('analysis_count', 0) // 7 + i % 3) for i in range(7)],
            'Issues Found': [max(0, analytics_data.get('total_issues', 0) // 7 + (i * 2) % 5) for i in range(7)]
        })
        
        fig_timeline = px.line(
            timeline_data,
            x='Date',
            y=['Analyses', 'Issues Found'],
            title='Analysis Activity Over Time',
            markers=True
        )
        
        fig_timeline.update_layout(
            height=400,
            xaxis_title="Date",
            yaxis_title="Count",
            legend_title="Metrics"
        )
        
        st.plotly_chart(fig_timeline, use_container_width=True)
        
        # Performance metrics
        st.markdown("### 🚀 Performance Metrics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            successful_analyses = analytics_data.get('successful_analyses', 0)
            failed_analyses = analytics_data.get('failed_analyses', 0)
            
            # Success vs Failure chart
            success_data = pd.DataFrame({
                'Status': ['Successful', 'Failed'],
                'Count': [successful_analyses, failed_analyses],
                'Color': ['#10b981', '#ef4444']
            })
            
            if successful_analyses > 0 or failed_analyses > 0:
                fig_success = px.pie(
                    success_data,
                    values='Count',
                    names='Status',
                    title='Analysis Success Rate',
                    color='Status',
                    color_discrete_map={'Successful': '#10b981', 'Failed': '#ef4444'}
                )
                
                fig_success.update_layout(height=300)
                st.plotly_chart(fig_success, use_container_width=True)
            else:
                st.info("No analysis data available")
        
        with col2:
            # Analysis statistics table
            st.markdown("#### 📋 Detailed Statistics")
            
            # Format values as strings to avoid Arrow serialization issues
            stats_data = {
                'Metric': [
                    'Total Analyses',
                    'Successful',
                    'Failed',
                    'Success Rate',
                    'Average Duration',
                    'Security Issues',
                    'Quality Issues',
                    'Logic Issues'
                ],
                'Value': [
                    str(analytics_data.get('analysis_count', 0)),
                    str(analytics_data.get('successful_analyses', 0)),
                    str(analytics_data.get('failed_analyses', 0)),
                    f"{analytics_data.get('success_rate', 0)}%",
                    f"{analytics_data.get('avg_duration', 0):.1f}s",
                    str(issue_types.get('security', 0)),
                    str(issue_types.get('quality', 0)),
                    str(issue_types.get('logic', 0))
                ]
            }
            
            stats_df = pd.DataFrame(stats_data)
            # Use column_config to ensure proper display
            st.dataframe(
                stats_df, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "Metric": st.column_config.TextColumn("Metric"),
                    "Value": st.column_config.TextColumn("Value")
                }
            )

# Footer
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #6b7280; padding: 2rem 0;">
        <p>🚀 <strong>PatchPilot</strong> - AI-Powered Code Review Platform</p>
        <p>Built with ❤️ using Streamlit</p>
    </div>
    """,
    unsafe_allow_html=True
)

# Auto-refresh for active analyses
if st.session_state.task_ids:
    # Add a subtle auto-refresh mechanism
    if st.button("🔄 Refresh Status", help="Check status of running analyses"):
        st.rerun()
    
    # Show active tasks
    active_tasks = []
    for task_type, task_id in st.session_state.task_ids.items():
        if task_id:
            result, error = make_request(f"api/analysis/status/{task_id}")
            if not error and result.get('status') in ['queued', 'processing']:
                active_tasks.append(f"{task_type.title()}: {task_id[:8]}...")
    
    if active_tasks:
        with st.sidebar:
            st.markdown("### 🔄 Active Analyses")
            for task in active_tasks:
                st.markdown(f"- {task}")
            
            if st.button("⏹️ Clear Completed", help="Clear completed task IDs"):
                st.session_state.task_ids = {}
                st.rerun()