import streamlit as st
import utils
import pandas as pd
from datetime import datetime
import time

def map_decision_to_status(decision):
    """Map backend decision to frontend status"""
    if decision == "APPROVE":
        return "approved"
    elif decision == "REJECT":
        return "blocked"
    elif decision == "REQUEST_CHANGES":
        return "warning"
    else:
        return "unknown"

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
                    "analysis_mode": analysis_mode.lower().replace(" ", "_")
                }
                
                status_text.text("Sending analysis request to backend...")
                progress_bar.progress(20)
                
                response = utils.call_backend_api("/api/analysis/pr", analysis_data, "POST")
                
                # Handle 202 response (task started)
                if response["status"] == "success" and "task_id" in response.get("data", {}):
                    task_id = response["data"]["task_id"]
                    status_text.text("Analysis in progress...")
                    progress_bar.progress(40)
                    
                    # Poll for results
                    max_attempts = 30  # 30 attempts with 2 second intervals = 1 minute max
                    attempt = 0
                    
                    while attempt < max_attempts:
                        time.sleep(2)  # Wait 2 seconds between checks
                        attempt += 1
                        
                        # Check task status
                        status_response = utils.call_backend_api(f"/api/analysis/status/{task_id}", {}, "GET")
                        
                        if status_response["status"] == "success":
                            task_status = status_response["data"]["status"]
                            
                            if task_status == "completed":
                                progress_bar.progress(100)
                                status_text.text("Analysis complete!")
                                
                                # Store results - map backend format to frontend format
                                backend_results = status_response["data"]["results"]
                                decision_info = backend_results.get("decision", {})
                                
                                mapped_results = {
                                    "security_findings": backend_results.get("security_issues", []),
                                    "quality_issues": backend_results.get("quality_issues", []),
                                    "logic_issues": backend_results.get("logic_issues", []),
                                    "overall_status": map_decision_to_status(decision_info.get("decision", "unknown")),
                                    "decision_info": decision_info,
                                    "recommendations": [
                                        {"type": "info", "message": rec} 
                                        for rec in decision_info.get("recommendations", [])
                                    ],
                                    "pr_details": status_response["data"].get("pr_details", {}),
                                    "pr_analysis": status_response["data"].get("pr_analysis", {})
                                }
                                
                                st.session_state.current_analysis = mapped_results
                                st.session_state.analysis_history.append({
                                    "pr_url": pr_url,
                                    "timestamp": datetime.now(),
                                    "analysis_mode": analysis_mode,
                                    "status": mapped_results["overall_status"]
                                })
                                
                                st.success("PR Analysis Complete!")
                                st.rerun()  # Refresh to show results
                                break
                            elif task_status == "error":
                                error_msg = status_response["data"].get("error", "Unknown error")
                                st.error(f"Analysis failed: {error_msg}")
                                break
                            else:
                                # Still processing
                                progress = min(40 + (attempt * 2), 90)
                                progress_bar.progress(progress)
                                status_text.text(f"Analyzing... ({task_status})")
                        else:
                            st.error(f"Failed to check status: {status_response.get('message', 'Unknown error')}")
                            break
                    
                    if attempt >= max_attempts:
                        st.error("Analysis timed out. Please try again.")
                        
                else:
                    st.error(f"Failed to start analysis: {response.get('message', 'Unknown error')}")
    
    # Display Analysis Results
    if st.session_state.current_analysis:
        results = st.session_state.current_analysis
        
        st.subheader("Analysis Results")
        
        # Overall Status
        overall_status = results.get("overall_status", "unknown")
        decision_info = results.get("decision_info", {})
        
        if overall_status == "approved":
            st.success("✅ APPROVED FOR MERGE")
        elif overall_status == "blocked":
            st.error("❌ MERGE BLOCKED - Critical issues found")
        elif overall_status == "warning":
            st.warning("⚠️ MERGE WITH CAUTION - Review issues carefully")
        else:
            st.info("ℹ️ Analysis completed - Review results below")
        
        # Show decision summary
        if decision_info:
            with st.expander("Decision Summary", expanded=True):
                st.write(f"**Decision:** {decision_info.get('decision', 'Unknown')}")
                st.write(f"**Risk Level:** {decision_info.get('risk_level', 'Unknown')}")
                st.write(f"**Summary:** {decision_info.get('summary', 'No summary available')}")
        
        # PR Details
        if results.get("pr_details"):
            pr_details = results["pr_details"]
            with st.expander("PR Information"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Title:** {pr_details.get('title', 'N/A')}")
                    st.write(f"**Author:** {pr_details.get('user', {}).get('login', 'N/A')}")
                    st.write(f"**State:** {pr_details.get('state', 'N/A')}")
                with col2:
                    st.write(f"**Files Changed:** {pr_details.get('changed_files', 'N/A')}")
                    st.write(f"**Additions:** +{pr_details.get('additions', 0)}")
                    st.write(f"**Deletions:** -{pr_details.get('deletions', 0)}")
        
        # Security Findings
        if "security_findings" in results:
            st.subheader("🔒 Security Analysis")
            security_findings = results["security_findings"]
            
            if security_findings:
                # Group by severity
                critical_issues = [f for f in security_findings if f.get("severity", "").lower() == "critical"]
                high_issues = [f for f in security_findings if f.get("severity", "").lower() == "high"]
                medium_issues = [f for f in security_findings if f.get("severity", "").lower() == "medium"]
                low_issues = [f for f in security_findings if f.get("severity", "").lower() == "low"]
                
                # Display critical issues first
                if critical_issues:
                    st.error(f"🚨 {len(critical_issues)} Critical Security Issues")
                    for finding in critical_issues:
                        with st.expander(f"CRITICAL: {finding.get('type', 'Unknown')}", expanded=True):
                            st.write(f"**File:** {finding.get('file', 'Unknown')}")
                            st.write(f"**Description:** {finding.get('description', 'No description')}")
                            st.write(f"**Confidence:** {finding.get('confidence', 'Unknown')}")
                
                # Display high issues
                if high_issues:
                    st.warning(f"⚠️ {len(high_issues)} High Severity Issues")
                    for finding in high_issues:
                        with st.expander(f"HIGH: {finding.get('type', 'Unknown')}"):
                            st.write(f"**File:** {finding.get('file', 'Unknown')}")
                            st.write(f"**Description:** {finding.get('description', 'No description')}")
                            st.write(f"**Confidence:** {finding.get('confidence', 'Unknown')}")
                
                # Display medium and low issues
                if medium_issues or low_issues:
                    with st.expander(f"Other Issues ({len(medium_issues + low_issues)} total)"):
                        for finding in medium_issues + low_issues:
                            st.write(f"**{finding.get('severity', 'Unknown').upper()}:** {finding.get('type', 'Unknown')}")
                            st.write(f"File: {finding.get('file', 'Unknown')}")
                            st.write(f"Description: {finding.get('description', 'No description')}")
                            st.write("---")
            else:
                st.success("✅ No security issues found!")
        
        # Quality Issues
        if "quality_issues" in results:
            st.subheader("📊 Code Quality Analysis")
            quality_issues = results["quality_issues"]
            
            if quality_issues:
                # Create a summary
                high_quality = [q for q in quality_issues if q.get("severity", "").lower() == "high"]
                medium_quality = [q for q in quality_issues if q.get("severity", "").lower() == "medium"]
                
                if high_quality:
                    st.warning(f"⚠️ {len(high_quality)} High Priority Quality Issues")
                
                # Display as expandable items
                for issue in quality_issues:
                    severity = issue.get("severity", "unknown").lower()
                    severity_icon = "🔴" if severity == "high" else "🟡" if severity == "medium" else "🟢"
                    
                    with st.expander(f"{severity_icon} {issue.get('type', 'Unknown')} - {issue.get('file', 'Unknown')}"):
                        st.write(f"**Severity:** {issue.get('severity', 'Unknown')}")
                        st.write(f"**Description:** {issue.get('description', 'No description')}")
                        st.write(f"**Confidence:** {issue.get('confidence', 'Unknown')}")
            else:
                st.success("✅ No quality issues found!")
        
        # Logic Issues
        if "logic_issues" in results:
            st.subheader("🧠 Logic Analysis")
            logic_issues = results["logic_issues"]
            
            if logic_issues:
                for issue in logic_issues:
                    with st.expander(f"Logic Issue - {issue.get('file', 'Unknown')}"):
                        st.write(f"**Analysis:** {issue.get('analysis', 'No analysis')}")
                        if issue.get('suggestions'):
                            st.write("**Suggestions:**")
                            for suggestion in issue['suggestions']:
                                st.write(f"- {suggestion}")
            else:
                st.success("✅ No logic issues found!")
        
        # Recommendations
        if "recommendations" in results and results["recommendations"]:
            st.subheader("💡 Recommendations")
            recommendations = results["recommendations"]
            
            for rec in recommendations:
                rec_type = rec.get("type", "info")
                message = rec.get("message", "No message")
                
                if rec_type == "critical":
                    st.error(f"🚨 {message}")
                elif rec_type == "warning":
                    st.warning(f"⚠️ {message}")
                elif rec_type == "success":
                    st.success(f"✅ {message}")
                else:
                    st.info(f"ℹ️ {message}")
        
        # Additional Analysis Data
        if results.get("pr_analysis"):
            pr_analysis = results["pr_analysis"]
            with st.expander("Detailed Analysis Metrics"):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Complexity Score", pr_analysis.get("complexity_score", "N/A"))
                    st.metric("Files Changed", len(pr_analysis.get("files_changed", [])))
                with col2:
                    st.metric("Total Lines Changed", pr_analysis.get("total_lines_changed", "N/A"))
                    st.metric("Large Files", len(pr_analysis.get("large_files", [])))
                
                if pr_analysis.get("large_files"):
                    st.write("**Large Files:**")
                    for file in pr_analysis["large_files"]:
                        st.write(f"- {file['filename']}: {file['changes']} changes")
    
    # Analysis History
    if st.session_state.analysis_history:
        st.subheader("📈 Analysis History")
        
        # Create a DataFrame for history
        history_data = []
        for entry in st.session_state.analysis_history[-10:]:  # Show last 10
            history_data.append({
                "PR URL": entry["pr_url"],
                "Mode": entry["analysis_mode"],
                "Status": entry.get("status", "Unknown"),
                "Timestamp": entry["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
            })
        
        if history_data:
            df = pd.DataFrame(history_data)
            st.dataframe(df, use_container_width=True)
        
        # Clear history button
        if st.button("Clear History"):
            st.session_state.analysis_history = []
            st.rerun()