import streamlit as st
import utils
from components import sidebar
from pages import (
    dashboard,
    pr_analysis,
    repository_manager,
    analytics,
    agent_configuration,
    settings
)

# Page configuration
st.set_page_config(
    page_title="PatchPilot AI - Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom styles
utils.apply_custom_styles()

# Initialize session state
utils.init_session_state()

# Handle rerun trigger early
if st.session_state.get("refresh_triggered"):
    st.session_state.refresh_triggered = False  # Reset the flag
    st.experimental_rerun()
    st.stop()  # Prevent further execution in this run cycle

# Render sidebar and get current page
current_page = sidebar.render_sidebar()

# Route to the selected page
if current_page == "Dashboard":
    dashboard.show()
elif current_page == "PR Analysis":
    pr_analysis.show()
elif current_page == "Repository Manager":
    repository_manager.show()
elif current_page == "Analytics":
    analytics.show()
elif current_page == "Agent Configuration":
    agent_configuration.show()
elif current_page == "Settings":
    settings.show()
