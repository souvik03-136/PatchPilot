import streamlit as st
import utils
import pandas as pd

def show():
    """Show dashboard page"""
    # Header
    st.markdown("""
        <div class="main-header">
            <h1 style="color: white; margin: 0;">CodeSentinel AI Dashboard</h1>
            <p style="color: white; margin: 10px 0 0 0;">Advanced Code Quality Guardian with AI Intelligence</p>
        </div>
    """, unsafe_allow_html=True)
    
    # System Status Overview
    if st.session_state.backend_connected:
        with st.spinner("Loading system metrics..."):
            metrics_response = utils.call_backend_api("/api/metrics")
            
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
    
    if st.session_state.backend_connected:
        with st.spinner("Loading agent status..."):
            agent_response = utils.call_backend_api("/api/agents/status")
            
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
    
    if st.session_state.backend_connected:
        with st.spinner("Loading repositories..."):
            repo_response = utils.call_backend_api("/api/repositories")
            
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