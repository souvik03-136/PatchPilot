import os
import sys
import time

from dotenv import load_dotenv

# Add root to path so `agents` can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from agents.models import (
    AnalysisContext, CodeSnippet, Vulnerability, QualityIssue, 
    AgentResponse, WorkflowState
)
from agents.workflows import create_analysis_workflow

# Load environment variables
load_dotenv()


class MockSecurityAgent:
    """Mock security agent that simulates analysis without API calls"""
    
    def analyze(self, state: WorkflowState) -> dict:
        """Simulate security analysis"""
        print("🔒 Mock Security Agent: Analyzing code...")
        
        # Simulate finding security issues
        vulnerabilities = []
        for snippet in state.context.code_snippets:
            if 'admin_pass' in snippet.content:
                vulnerabilities.append(Vulnerability(
                    type="Hardcoded Credentials",
                    severity="high",
                    description="Hardcoded password found in source code",
                    line=2,
                    file=snippet.file_path,
                    confidence=0.95
                ))
            
            if 'eval(' in snippet.content:
                vulnerabilities.append(Vulnerability(
                    type="Code Injection",
                    severity="critical",
                    description="Use of eval() function is dangerous",
                    line=1,
                    file=snippet.file_path,
                    confidence=0.9
                ))
        
        return {"security_results": vulnerabilities}


class MockQualityAgent:
    """Mock quality agent that simulates analysis without API calls"""
    
    def analyze(self, state: WorkflowState) -> dict:
        """Simulate quality analysis"""
        print("📊 Mock Quality Agent: Analyzing code quality...")
        
        quality_issues = []
        for snippet in state.context.code_snippets:
            # Simulate finding quality issues
            if len(snippet.content.split('\n')) > 10:
                quality_issues.append(QualityIssue(
                    type="Function Length",
                    description="Function is too long, consider breaking it down",
                    line=1,
                    file=snippet.file_path,
                    severity="medium",
                    rule_id="C901"
                ))
            
            if 'for item in data:' in snippet.content:
                quality_issues.append(QualityIssue(
                    type="Code Complexity",
                    description="Complex nested logic detected",
                    line=3,
                    file=snippet.file_path,
                    severity="low",
                    rule_id="C903"
                ))
        
        return {"quality_results": quality_issues}


class MockLogicAgent:
    """Mock logic agent that simulates analysis without API calls"""
    
    def analyze(self, state: WorkflowState) -> dict:
        """Simulate logic analysis"""
        print("🧠 Mock Logic Agent: Analyzing logic...")
        
        logic_results = []
        for snippet in state.context.code_snippets:
            logic_results.append({
                "file": snippet.file_path,
                "analysis": f"Logic analysis for {snippet.file_path}: The function appears to handle data processing with conditional logic.",
                "suggestions": [
                    "Consider using list comprehension for better readability",
                    "Add input validation",
                    "Consider using more descriptive variable names"
                ],
                "complexity_score": 3.2
            })
        
        return {"logic_results": logic_results}


class MockContextAgent:
    """Mock context agent that simulates enrichment without API calls"""
    
    def enrich_context(self, state: WorkflowState) -> dict:
        """Simulate context enrichment"""
        print("📚 Mock Context Agent: Enriching context...")
        
        enriched_context = {
            "repo_analysis": {
                "total_files": len(state.context.code_snippets),
                "languages": list(set(snippet.language for snippet in state.context.code_snippets)),
                "risk_score": 7.5
            },
            "historical_patterns": {
                "similar_issues": len(state.context.previous_issues),
                "author_history": f"Author {state.context.author} has moderate risk profile"
            },
            "code_metrics": {
                "total_lines": sum(len(snippet.content.split('\n')) for snippet in state.context.code_snippets),
                "avg_function_length": 8.5
            }
        }
        
        return {"enriched_context": enriched_context}


class MockDecisionAgent:
    """Mock decision agent that simulates decision making without API calls"""
    
    def make_decision(self, state: WorkflowState) -> dict:
        """Simulate decision making"""
        print("⚖️  Mock Decision Agent: Making decision...")
        
        # Calculate risk based on findings
        critical_issues = len([issue for issue in state.security_results if issue.severity == "critical"])
        high_issues = len([issue for issue in state.security_results if issue.severity == "high"])
        
        if critical_issues > 0:
            decision = "REJECT"
            risk_level = "HIGH"
        elif high_issues > 2:
            decision = "REVIEW_REQUIRED"
            risk_level = "MEDIUM"
        else:
            decision = "APPROVE"
            risk_level = "LOW"
        
        decision_data = {
            "decision": decision,
            "risk_level": risk_level,
            "summary": f"Found {critical_issues} critical and {high_issues} high severity issues",
            "recommendations": [
                "Fix all critical security issues before deployment",
                "Consider code review for quality improvements",
                "Add unit tests for complex logic"
            ]
        }
        
        return {"decision": decision_data}


def main():
    print("Starting Mock Agent System Test (No API Calls)")
    
    # Create mock agents
    mock_agents = {
        "security": MockSecurityAgent(),
        "quality": MockQualityAgent(),
        "logic": MockLogicAgent(),
        "context": MockContextAgent(),
        "decision": MockDecisionAgent()
    }
    
    print("Mock agent system initialized")

    # Dummy context for testing
    context = AnalysisContext(
        repo_name="test-repo",
        pr_id="123",
        author="test-user",
        commit_history=[{"id": "abc123", "message": "Initial commit"}],
        previous_issues=[
            Vulnerability(
                type="Hardcoded Secret",
                severity="high",
                description="Password in source code",
                line=42,
                file="config.py"
            )
        ],
        code_snippets=[
            CodeSnippet(
                file_path="app.py",
                content="""def login(username, password):
    admin_pass = 'superSecret123'
    if password == admin_pass:
        return True
    return False""",
                language="python"
            ),
            CodeSnippet(
                file_path="utils.py",
                content="""def process_data(data):
    result = []
    for item in data:
        if item['status'] == 'active':
            if item['value'] > 100:
                result.append(item['value'] * 1.1)
            else:
                result.append(item['value'] * 0.9)
        else:
            result.append(None)
    return result""",
                language="python"
            )
        ]
    )

    print("\nStarting analysis...")
    start_time = time.time()

    # Create and invoke workflow
    workflow = create_analysis_workflow(mock_agents)
    initial_state = WorkflowState(context=context)
    
    # LangGraph workflow.invoke() returns a dictionary, not a WorkflowState object
    result_dict = workflow.invoke(initial_state)
    
    # Convert the result dictionary back to WorkflowState object for easier access
    # or access the values directly from the dictionary
    security_results = result_dict.get("security_results", [])
    quality_results = result_dict.get("quality_results", [])
    logic_results = result_dict.get("logic_results", [])
    enriched_context = result_dict.get("enriched_context", {})
    decision = result_dict.get("decision", {})

    duration = time.time() - start_time
    print(f"\nAnalysis completed in {duration:.2f} seconds")

    # Output results
    print("\n" + "="*50)
    print("ANALYSIS RESULTS")
    print("="*50)
    
    print(f"\nSecurity Issues ({len(security_results)}):")
    for issue in security_results:
        print(f"- [{issue.severity.upper()}] {issue.type}: {issue.description} ({issue.file}:{issue.line})")

    print(f"\nQuality Issues ({len(quality_results)}):")
    for issue in quality_results:
        print(f"- [{issue.severity.upper()}] {issue.type}: {issue.description} ({issue.file}:{issue.line})")

    print(f"\nLogic Analysis ({len(logic_results)}):")
    for issue in logic_results:
        if isinstance(issue, dict):
            print(f"- File: {issue.get('file', 'Unknown')}")
            print(f"  Complexity Score: {issue.get('complexity_score', 'N/A')}")
            print(f"  Suggestions: {len(issue.get('suggestions', []))}")
        else:
            print(f"- Issue: {issue}")

    print("\nEnriched Context:")
    if enriched_context:
        for key, value in enriched_context.items():
            print(f"- {key}: {value}")

    print("\nDecision:")
    if isinstance(decision, dict):
        print(f"Decision: {decision.get('decision', 'N/A')}")
        print(f"Risk Level: {decision.get('risk_level', 'N/A')}")
        print(f"Summary: {decision.get('summary', 'No summary')}")
        if decision.get('recommendations'):
            print("Recommendations:")
            for rec in decision['recommendations']:
                print(f"  • {rec}")
    else:
        print(f"Decision: {decision}")

    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    print(f"Total Security Issues: {len(security_results)}")
    print(f"Total Quality Issues: {len(quality_results)}")
    print(f"Total Logic Issues: {len(logic_results)}")
    
    # Check for critical issues
    critical_security = [issue for issue in security_results if issue.severity == "critical"]
    if critical_security:
        print(f"⚠️  CRITICAL: {len(critical_security)} critical security issues found!")
    else:
        print("✅ No critical security issues found")
    
    print("✅ Mock test completed successfully!")


if __name__ == "__main__":
    main()