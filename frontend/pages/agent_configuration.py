
import streamlit as st
import utils

def show():
    """Show Agent Configuration page"""
    st.header("Agent Configuration")
    
    if not st.session_state.backend_connected:
        st.error("Backend not connected. Please start the backend server to configure agents.")
    else:
        with st.spinner("Loading agent configurations..."):
            config_response = utils.call_backend_api("/api/agents/config")
            
            if config_response["status"] == "success":
                agent_configs = config_response["data"]
                
                for agent_name, config in agent_configs.items():
                    with st.expander(f"{agent_name.title()} Agent Configuration"):
                        # Configuration form for each agent
                        model = st.selectbox(
                            f"Model", 
                            ["codellama:13b", "mistral:7b", "qwen-coder:7b"], 
                            index=0,
                            key=f"model_{agent_name}"
                        )
                        
                        sensitivity = st.slider(
                            f"Sensitivity", 
                            0.1, 1.0, 0.8,
                            key=f"sensitivity_{agent_name}"
                        )
                        
                        autofix = st.checkbox(
                            f"Auto-fix enabled", 
                            key=f"autofix_{agent_name}"
                        )
                        
                        if st.button(f"Save {agent_name.title()} Config", key=f"save_{agent_name}"):
                            # Save configuration via API
                            save_config_data = {
                                "agent": agent_name,
                                "model": model,
                                "sensitivity": sensitivity,
                                "autofix": autofix
                            }
                            
                            save_response = utils.call_backend_api("/api/agents/config", save_config_data, "POST")
                            
                            if save_response["status"] == "success":
                                st.success(f"{agent_name.title()} configuration saved!")
                            else:
                                st.error("Failed to save configuration")
            else:
                st.error("Unable to load agent configurations")