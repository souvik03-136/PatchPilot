import streamlit as st
import utils
import pandas as pd
from datetime import datetime

def show():
    """Show PR Analysis page"""
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
                
                response = utils.call_backend_api("/api/analysis/pr", analysis_data, "POST")
                
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