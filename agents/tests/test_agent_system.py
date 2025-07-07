import os
import sys
import time

# Ensure root directory is in Python path so 'agents' module can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from dotenv import load_dotenv
from agents import AgentSystem
from agents.models import AnalysisContext, CodeSnippet, Vulnerability

# Load environment variables
load_dotenv()

def main():
    print("🚀 Starting Free LLM Agent System Test")
    
    # Initialize agent system with Gemini provider
    agent_system = AgentSystem(provider="gemini")
    print("✅ Agent system initialized with Gemini")
    
    # Create test context
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
    # Security vulnerability - hardcoded secret!
    admin_pass = 'superSecret123'
    if password == admin_pass:
        return True
    return False""",
                language="python"
            ),
            CodeSnippet(
                file_path="utils.py",
                content="""# Overly complex function
def process_data(data):
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
    
    print("\n🔍 Starting analysis...")
    start_time = time.time()
    results = agent_system.analyze_pull_request(context)
    duration = time.time() - start_time
    print(f"⏱️ Analysis completed in {duration:.2f} seconds")
    
    # Print results
    print("\n📊 Security Issues:")
    for issue in results.get("security_issues", []):
        print(f"- [{issue.severity.upper()}] {issue.type}: {issue.description}")
        print(f"  File: {issue.file}:{issue.line}")
    
    print("\n📝 Quality Issues:")
    for issue in results.get("quality_issues", []):
        print(f"- [{issue.severity.upper()}] {issue.type}: {issue.description}")
        print(f"  File: {issue.file}:{issue.line}")
    
    print("\n🤔 Logic Analysis:")
    for issue in results.get("logic_issues", []):
        print(f"- File: {issue['file']}")
        print(f"  Analysis: {issue['analysis'][:100]}...")
        if issue['suggestions']:
            print(f"  Suggestions: {len(issue['suggestions'])} code blocks")
    
    print("\n📋 Decision:")
    decision = results.get("decision", {})
    print(f"Decision: {decision.get('decision', 'N/A')}")
    print(f"Risk Level: {decision.get('risk_level', 'N/A')}")
    print(f"Summary: {decision.get('summary', 'No summary')}")
    
    print("\n🔄 Agent Status:")
    status = agent_system.get_agent_status()
    print(f"Provider: {status['provider']}")
    for agent, state in status["agents"].items():
        print(f"- {agent}: {state}")

if __name__ == "__main__":
    main()
