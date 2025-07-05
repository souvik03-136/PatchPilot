import streamlit as st
import utils

def show():
    """Show Settings page"""
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
                
                response = utils.call_backend_api("/api/settings/github", settings_data, "POST")
                
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
                
                response = utils.call_backend_api("/api/settings/notifications", notification_data, "POST")
                
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
                
                response = utils.call_backend_api("/api/settings/security", security_data, "POST")
                
                if response["status"] == "success":
                    st.success("Security settings saved!")
                else:
                    st.error("Failed to save security settings")