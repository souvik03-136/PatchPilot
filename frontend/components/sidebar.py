import streamlit as st
import requests
from requests.exceptions import RequestException
import utils

def render_sidebar():
    """Render the sidebar navigation"""
    st.sidebar.markdown("### Navigation")
    page = st.sidebar.selectbox(
        "Select Page",
        ["Dashboard", "PR Analysis", "Repository Manager", "Analytics", "Agent Configuration", "Settings"]
    )
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### System Status")
    
    if st.session_state.get("backend_connected"):
        st.sidebar.success("Backend: Connected")
    else:
        st.sidebar.error("Backend: Disconnected")
    
    # Backend URL configuration
    st.sidebar.markdown("### Backend Configuration")
    new_backend_url = st.sidebar.text_input("Backend URL", value=st.session_state.backend_url)

    if not new_backend_url.startswith("http"):
        st.sidebar.warning("Please enter a valid URL (e.g., http://localhost:8000)")
    
    if st.sidebar.button("Test Connection"):
        try:
            response = requests.get(f"{new_backend_url}/health", timeout=5)
            if response.status_code == 200:
                st.sidebar.success("Connection successful!")
                st.session_state.backend_url = new_backend_url
            else:
                st.sidebar.error("Connection failed!")
        except RequestException:
            st.sidebar.error("Connection failed!")
    
    if st.sidebar.button("Refresh Dashboard"):
        st.session_state.refresh_triggered = True

    return page
