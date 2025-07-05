import streamlit as st
import utils

def show():
    """Show Analytics page"""
    st.header("Analytics & Reporting")
    
    if not st.session_state.backend_connected:
        st.error("Backend not connected. Please start the backend server to view analytics.")
    else:
        # Time range selector
        time_range = st.selectbox("Time Range", ["Last 7 days", "Last 30 days", "Last 90 days", "All time"])
        
        with st.spinner("Loading analytics data..."):
            analytics_response = utils.call_backend_api(f"/api/analytics?range={time_range}")
            
            if analytics_response["status"] == "success":
                analytics_data = analytics_response["data"]
                
                # Display analytics charts
                st.subheader("Issue Trends")
                
                if "issue_trends" in analytics_data:
                    # Create charts from real data
                    st.info("Analytics data loaded successfully")
                    # Placeholder for actual chart implementation
                    st.line_chart(analytics_data["issue_trends"])
                else:
                    st.info("No analytics data available yet")
            else:
                st.error("Unable to load analytics data")