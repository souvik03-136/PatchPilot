import streamlit as st
import utils

def show():
    """Show Repository Manager page"""
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
                
                response = utils.call_backend_api("/api/repositories", add_repo_data, "POST")
                
                if response["status"] == "success":
                    st.success("Repository added successfully!")
                    st.experimental_rerun()
                else:
                    st.error(f"Failed to add repository: {response['message']}")
    
    # Repository List
    st.subheader("Connected Repositories")
    
    if st.session_state.backend_connected:
        response = utils.call_backend_api("/api/repositories")
        
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
                            remove_response = utils.call_backend_api(f"/api/repositories/{repo.get('id')}", method="DELETE")
                            if remove_response["status"] == "success":
                                st.success("Repository removed!")
                                st.experimental_rerun()
                            else:
                                st.error("Failed to remove repository")
                    
                    st.divider()
            else:
                st.info("No repositories connected yet. Add your first repository above.")
        else:
            st.error("Unable to load repositories")
    else:
        st.error("Backend not connected")