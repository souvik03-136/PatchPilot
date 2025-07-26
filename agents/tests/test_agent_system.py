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

load_dotenv()


class MockSecurityAgent:
    def analyze(self, state: WorkflowState) -> dict:
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
    def analyze(self, state: WorkflowState) -> dict:
        quality_issues = []
        for snippet in state.context.code_snippets:
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
    def analyze(self, state: WorkflowState) -> dict:
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
    def enrich_context(self, state: WorkflowState) -> dict:
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
    def make_decision(self, state: WorkflowState) -> dict:
        critical_issues = len([issue for issue in state.security_results if issue.severity == "critical"])
        high_issues = len([issue for issue in state.security_results if issue.severity == "high"])

        if critical_issues > 0:
            decision = "BLOCK"
            risk_level = "HIGH"
        elif high_issues > 2:
            decision = "REQUEST_CHANGES"
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
    print("Starting Mock Agent System Test")

    mock_agents = {
        "security": MockSecurityAgent(),
        "quality": MockQualityAgent(),
        "logic": MockLogicAgent(),
        "context": MockContextAgent(),
        "decision": MockDecisionAgent()
    }

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

    print("Running analysis...")
    start_time = time.time()

    workflow = create_analysis_workflow(mock_agents)
    initial_state = WorkflowState(context=context)
    result_dict = workflow.invoke(initial_state)

    security_results = result_dict.get("security_results", [])
    quality_results = result_dict.get("quality_results", [])
    logic_results = result_dict.get("logic_results", [])
    enriched_context = result_dict.get("enriched_context", {})
    decision = result_dict.get("decision", {})

    duration = time.time() - start_time
    print(f"\nAnalysis completed in {duration:.2f} seconds")

    print("\nANALYSIS RESULTS")
    print("-" * 50)

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

    print("\nSUMMARY")
    print("-" * 50)
    print(f"Total Security Issues: {len(security_results)}")
    print(f"Total Quality Issues: {len(quality_results)}")
    print(f"Total Logic Issues: {len(logic_results)}")

    critical_security = [issue for issue in security_results if issue.severity == "critical"]
    if critical_security:
        print(f"CRITICAL: {len(critical_security)} critical security issues found!")
    else:
        print("No critical security issues found")

    print("Mock test completed successfully.")


if __name__ == "__main__":
    main()