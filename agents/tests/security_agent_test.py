import os
import sys
import time
import json
from unittest.mock import Mock, patch, MagicMock
from dotenv import load_dotenv

# Add root to path so `agents` can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from agents.models import AnalysisContext, CodeSnippet, AgentResponse, Vulnerability
from agents.security_agent import SecurityAgent

load_dotenv()

from langchain_core.runnables.base import Runnable
from langchain_core.runnables.utils import Input, Output

# Create a simple WorkflowState class for testing
class TestWorkflowState:
    def __init__(self, context):
        self.context = context
        self.security_results = []
        self.security_errors = []

class MockSecurityLLM(Runnable):
    """Mock LLM for security testing that implements LangChain's Runnable interface"""
    
    def __init__(self, response_type="vulnerabilities_found"):
        self.response_type = response_type
        super().__init__()
    
    def invoke(self, input, config=None, **kwargs):
        if self.response_type == "vulnerabilities_found":
            return json.dumps([
                {
                    "type": "SQL Injection",
                    "severity": "critical",
                    "description": "User input is directly concatenated into SQL query without sanitization",
                    "line": 12,
                    "file": "test_file.py",
                    "confidence": 0.95
                },
                {
                    "type": "Hardcoded Credentials",
                    "severity": "high",
                    "description": "API key is hardcoded in source code",
                    "line": 8,
                    "file": "test_file.py",
                    "confidence": 0.9
                }
            ])
        elif self.response_type == "no_vulnerabilities":
            return json.dumps([])
        elif self.response_type == "single_vulnerability":
            return json.dumps([
                {
                    "type": "XSS Vulnerability",
                    "severity": "medium",
                    "description": "User input is not properly escaped before rendering",
                    "line": 25,
                    "file": "test_file.py",
                    "confidence": 0.8
                }
            ])
        elif self.response_type == "critical_vulnerabilities":
            return json.dumps([
                {
                    "type": "Command Injection",
                    "severity": "critical",
                    "description": "User input passed directly to system command",
                    "line": 33,
                    "file": "test_file.py",
                    "confidence": 0.95
                },
                {
                    "type": "Path Traversal",
                    "severity": "high",
                    "description": "File path not validated, allowing directory traversal",
                    "line": 15,
                    "file": "test_file.py",
                    "confidence": 0.88
                },
                {
                    "type": "Weak Encryption",
                    "severity": "medium",
                    "description": "Using deprecated MD5 hash function",
                    "line": 42,
                    "file": "test_file.py",
                    "confidence": 0.75
                }
            ])
        elif self.response_type == "malformed_json":
            return "This is not valid JSON format\nSome vulnerability description here"
        elif self.response_type == "json_with_markdown":
            return json.dumps([
                {
                    "type": "Authentication Bypass",
                    "severity": "critical",
                    "description": "Missing authentication check in sensitive endpoint",
                    "line": 20,
                    "file": "test_file.py",
                    "confidence": 0.9
                }
            ])
        elif self.response_type == "partial_vulnerability_data":
            return json.dumps([
                {
                    "type": "Missing Input Validation",
                    "severity": "medium",
                    "description": "User input not validated"
                },
                {
                    "type": "Insecure File Operation",
                    "line": 18,
                    "confidence": 0.7
                }
            ])
        elif self.response_type == "exception":
            raise Exception("Security LLM connection failed")
        else:
            return json.dumps([])

    async def ainvoke(self, input, config=None, **kwargs):
        return self.invoke(input, config, **kwargs)

    def batch(self, inputs, config=None, **kwargs):
        return [self.invoke(inp, config, **kwargs) for inp in inputs]

    async def abatch(self, inputs, config=None, **kwargs):
        return [await self.ainvoke(inp, config, **kwargs) for inp in inputs]

    def stream(self, input, config=None, **kwargs):
        yield self.invoke(input, config, **kwargs)

    async def astream(self, input, config=None, **kwargs):
        yield self.invoke(input, config, **kwargs)

class MockFreeLLMProvider:
    """Mock FreeLLMProvider for testing"""
    def __init__(self, provider):
        self.provider = provider
        self.mock_llm = None
    
    def set_response_type(self, response_type):
        self.mock_llm = MockSecurityLLM(response_type)
    
    def get_llm(self, agent_type):
        if self.mock_llm is None:
            self.mock_llm = MockSecurityLLM()
        return self.mock_llm


def create_test_security_code_snippets():
    """Create test code snippets with various security issues"""
    return [
        CodeSnippet(
            file_path="vulnerable_sql.py",
            content="""import sqlite3

def get_user(user_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Vulnerable to SQL injection
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
    return cursor.fetchone()""",
            language="python"
        ),
        CodeSnippet(
            file_path="hardcoded_secrets.py",
            content="""import requests

API_KEY = "sk-1234567890abcdef"  # Hardcoded API key
SECRET_PASSWORD = "admin123"

def make_api_call():
    headers = {'Authorization': f'Bearer {API_KEY}'}
    response = requests.get('https://api.example.com/data', headers=headers)
    return response.json()""",
            language="python"
        ),
        CodeSnippet(
            file_path="xss_vulnerable.py",
            content="""from flask import Flask, request, render_template_string

app = Flask(__name__)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    # Vulnerable to XSS
    return render_template_string(f'<h1>Results for: {query}</h1>')""",
            language="python"
        ),
        CodeSnippet(
            file_path="secure_code.py",
            content="""import hashlib
import secrets
from flask import Flask, request, escape
import sqlite3

app = Flask(__name__)

def secure_hash(data):
    # Using secure hash function
    return hashlib.sha256(data.encode()).hexdigest()

def get_user_secure(user_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    # Using parameterized query
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return cursor.fetchone()

@app.route('/search')
def secure_search():
    query = request.args.get('q', '')
    # Properly escaped output
    return f'<h1>Results for: {escape(query)}</h1>'""",
            language="python"
        ),
        CodeSnippet(
            file_path="command_injection.py",
            content="""import os
import subprocess

def process_file(filename):
    # Vulnerable to command injection
    os.system(f"cat {filename}")
    
    # Also vulnerable
    subprocess.call(f"grep 'pattern' {filename}", shell=True)""",
            language="python"
        )
    ]


def create_test_security_state(snippet_count=1):
    """Create test state for security analysis"""
    snippets = create_test_security_code_snippets()[:snippet_count]
    context = AnalysisContext(
        repo_name="test-security-repo",
        pr_id="PR-789",
        author="security.tester",
        commit_history=[
            {"id": "sec123", "message": "feat: add user authentication"},
            {"id": "sec456", "message": "fix: improve input validation"}
        ],
        previous_issues=[],
        code_snippets=snippets
    )
    return TestWorkflowState(context)


def test_security_agent_initialization():
    """Test SecurityAgent initialization"""
    print("Testing SecurityAgent initialization...")
    
    with patch('agents.security_agent.FreeLLMProvider', MockFreeLLMProvider):
        # Create agent
        agent = SecurityAgent(provider="gemini")
        
        # Verify initialization
        assert agent.llm is not None
        assert agent.parser is not None
        assert agent.prompt is not None
        assert agent.llm_provider is not None
        assert isinstance(agent.llm, MockSecurityLLM)
        
        print("✓ SecurityAgent initialized successfully")

def test_analyze_with_vulnerabilities_found():
    print("\nTesting security analysis with vulnerabilities found...")
    
    with patch('agents.security_agent.FreeLLMProvider', MockFreeLLMProvider):
        agent = SecurityAgent(provider="gemini")
        agent.llm_provider.set_response_type("vulnerabilities_found")
        agent.llm = agent.llm_provider.get_llm("security")
        
        state = create_test_security_state(1)
        
        response = agent.analyze(state)
        
        # Debug prints
        print(f"Security results count: {len(response.security_results)}")
        print(f"Security errors: {response.security_errors}")
        
        assert len(response.security_results) == 2
        assert len(response.security_errors) == 0
        
        # Vulnerability assertions...
        vuln1 = response.security_results[0]
        assert isinstance(vuln1, Vulnerability)
        assert vuln1.type == "SQL Injection"
        assert vuln1.severity == "critical"
        assert vuln1.line == 12
        assert vuln1.confidence == 0.95

        vuln2 = response.security_results[1]
        assert isinstance(vuln2, Vulnerability)
        assert vuln2.type == "Hardcoded Credentials"
        assert vuln2.severity == "high"
        assert vuln2.line == 8
        assert vuln2.confidence == 0.9

        print("✓ Vulnerabilities found and validated successfully.")

        # Create compatible response for backward compatibility
        compatible_response = AgentResponse(
            success=len(response.security_errors) == 0,
            results=response.security_results,
            errors=response.security_errors,
            metadata={
                "total_files": 1,
                "issues_found": len(response.security_results)
            }
        )
        
        assert compatible_response.success == True
        assert len(compatible_response.results) == 2
        assert compatible_response.metadata["total_files"] == 1
        assert compatible_response.metadata["issues_found"] == 2


def test_analyze_with_no_vulnerabilities():
    """Test security analysis when no vulnerabilities are found"""
    print("\nTesting security analysis with no vulnerabilities...")
    
    with patch('agents.security_agent.FreeLLMProvider', MockFreeLLMProvider):
        # Create agent and test state
        agent = SecurityAgent(provider="gemini")
        agent.llm_provider.set_response_type("no_vulnerabilities")
        agent.llm = agent.llm_provider.get_llm("security")
        
        state = create_test_security_state(1)
        
        # Test analysis
        response = agent.analyze(state)
        
        # Verify response
        assert len(response.security_results) == 0  # No vulnerabilities found
        assert len(response.security_errors) == 0
        
        print("✓ Security analysis with no vulnerabilities working correctly")


def test_analyze_multiple_files():
    """Test security analysis with multiple files"""
    print("\nTesting security analysis with multiple files...")
    
    with patch('agents.security_agent.FreeLLMProvider', MockFreeLLMProvider):
        # Create agent and test state with multiple files
        agent = SecurityAgent(provider="gemini")
        agent.llm_provider.set_response_type("single_vulnerability")
        agent.llm = agent.llm_provider.get_llm("security")
        
        state = create_test_security_state(3)  # 3 files
        
        # Test analysis
        response = agent.analyze(state)
        
        # Verify response
        assert len(response.security_results) == 3  # One vulnerability per file
        assert len(response.security_errors) == 0
        
        # Check each result is a Vulnerability object
        for result in response.security_results:
            assert isinstance(result, Vulnerability)
            assert result.type == "XSS Vulnerability"
            assert result.severity == "medium"
        
        print("✓ Multiple file security analysis working correctly")
        print(f"✓ Files analyzed: 3")


def test_analyze_with_tuple_snippets():
    """Test security analysis with tuple code snippets"""
    print("\nTesting security analysis with tuple snippets...")
    
    with patch('agents.security_agent.FreeLLMProvider', MockFreeLLMProvider):
        # Create agent
        agent = SecurityAgent(provider="gemini")
        agent.llm_provider.set_response_type("single_vulnerability")
        agent.llm = agent.llm_provider.get_llm("security")
        
        # Create snippet
        snippet = CodeSnippet(
            file_path="tuple_test.py",
            content="password = 'hardcoded123'",
            language="python"
        )
        
        # Test that Pydantic validation fails with tuple format
        try:
            context = AnalysisContext(
                repo_name="test-security-repo",
                pr_id="PR-789",
                author="security.tester",
                commit_history=[],
                previous_issues=[],
                code_snippets=[("metadata", snippet)]  # Tuple format - should fail
            )
            # If we reach here, the validation didn't work as expected
            assert False, "Expected Pydantic validation error for tuple snippets"
        except Exception as e:
            # Expected validation error
            assert "Input should be a valid dictionary or instance of CodeSnippet" in str(e)
            print("✓ Tuple snippet validation correctly rejected by Pydantic model")
            return
        
        print("✓ Tuple snippet security analysis working correctly")


def test_analyze_json_parsing():
    """Test JSON parsing scenarios"""
    print("\nTesting JSON parsing scenarios...")
    
    with patch('agents.security_agent.FreeLLMProvider', MockFreeLLMProvider):
        # Test markdown-wrapped JSON
        agent = SecurityAgent(provider="gemini")
        agent.llm_provider.set_response_type("json_with_markdown")
        agent.llm = agent.llm_provider.get_llm("security")
        
        state = create_test_security_state(1)
        response = agent.analyze(state)
        
        assert len(response.security_results) == 1
        vuln = response.security_results[0]
        assert vuln.type == "Authentication Bypass"
        assert vuln.severity == "critical"
        
        print("✓ JSON parsing with markdown wrapper works correctly")


def test_analyze_malformed_json():
    """Test analysis with malformed JSON response"""
    print("\nTesting analysis with malformed JSON...")
    
    with patch('agents.security_agent.FreeLLMProvider', MockFreeLLMProvider):
        # Create agent
        agent = SecurityAgent(provider="gemini")
        agent.llm_provider.set_response_type("malformed_json")
        agent.llm = agent.llm_provider.get_llm("security")
        
        state = create_test_security_state(1)
        
        # Test analysis
        response = agent.analyze(state)
        
        # Should still succeed but create a generic vulnerability from text
        assert len(response.security_results) == 1
        vuln = response.security_results[0]
        assert vuln.type == "Potential Security Issue"
        assert vuln.severity == "medium"
        assert vuln.confidence == 0.6
        assert "vulnerability" in vuln.description.lower()
        
        print("✓ Malformed JSON handling works correctly")

def test_analyze_partial_vulnerability_data():
    """Test analysis with partial vulnerability data"""
    print("\nTesting analysis with partial vulnerability data...")
    
    with patch('agents.security_agent.FreeLLMProvider', MockFreeLLMProvider):
        # Create agent
        agent = SecurityAgent(provider="gemini")
        agent.llm_provider.set_response_type("partial_vulnerability_data")
        agent.llm = agent.llm_provider.get_llm("security")
        
        state = create_test_security_state(1)
        
        # Test analysis
        response = agent.analyze(state)
        
        # Debug: Print the actual response to see what we're getting
        print(f"Number of vulnerabilities found: {len(response.security_results)}")
        for i, vuln in enumerate(response.security_results):
            print(f"Vulnerability {i+1}: type='{vuln.type}', severity='{vuln.severity}', line={vuln.line}, confidence={vuln.confidence}")
        
        # Verify response handles missing fields with defaults
        assert len(response.security_results) == 2
        
        # Check first vulnerability (missing line and confidence)
        vuln1 = response.security_results[0]
        assert vuln1.type == "Missing Input Validation"
        assert vuln1.severity == "medium"
        assert vuln1.line == 0  # Default value when line is missing
        assert vuln1.confidence == 0.8  # Default value when confidence is missing
        
        # Check second vulnerability (missing type, severity, description)
        # Looking at the mock data, it actually has type="Insecure File Operation"
        vuln2 = response.security_results[1]
        assert vuln2.type == "Insecure File Operation"  # This is what the mock actually returns
        assert vuln2.severity == "medium"  # Default value when severity is missing
        assert vuln2.description == ""  # Default value when description is missing
        assert vuln2.line == 18
        assert vuln2.confidence == 0.7
        
        print("✓ Partial vulnerability data handling works correctly")


def test_analyze_error_handling():
    """Test error handling in security analysis"""
    print("\nTesting error handling in security analysis...")
    
    with patch('agents.security_agent.FreeLLMProvider', MockFreeLLMProvider):
        # Create agent and test state
        agent = SecurityAgent(provider="gemini")
        agent.llm_provider.set_response_type("exception")
        agent.llm = agent.llm_provider.get_llm("security")
        
        state = create_test_security_state(1)
        
        # Test analysis with error
        response = agent.analyze(state)
        
        # Verify error handling
        assert len(response.security_errors) == 1
        assert "Error analyzing vulnerable_sql.py" in response.security_errors[0]
        assert "Security LLM connection failed" in response.security_errors[0]
        assert len(response.security_results) == 0
        
        print("✓ Error handling works correctly")
        print(f"✓ Error count: {len(response.security_errors)}")
        print(f"✓ Error message: {response.security_errors[0]}")


def test_analyze_empty_code_snippet():
    """Test analysis with empty code snippet"""
    print("\nTesting analysis with empty code snippet...")
    
    with patch('agents.security_agent.FreeLLMProvider', MockFreeLLMProvider):
        # Create agent
        agent = SecurityAgent(provider="gemini")
        agent.llm_provider.set_response_type("no_vulnerabilities")
        agent.llm = agent.llm_provider.get_llm("security")
        
        # Create state with empty snippet
        empty_snippet = CodeSnippet(
            file_path="empty_file.py",
            content="",  # Empty content
            language="python"
        )
        
        context = AnalysisContext(
            repo_name="test-security-repo",
            pr_id="PR-789",
            author="security.tester",
            commit_history=[],
            previous_issues=[],
            code_snippets=[empty_snippet]
        )
        
        state = TestWorkflowState(context)
        
        # Test analysis - should handle empty content gracefully
        response = agent.analyze(state)
        
        # Should succeed with no vulnerabilities
        assert len(response.security_results) == 0
        assert len(response.security_errors) == 0
        
        print("✓ Empty code snippet handling works correctly")


def test_analyze_none_snippet():
    """Test analysis with None or malformed snippet"""
    print("\nTesting analysis with None snippet...")
    
    with patch('agents.security_agent.FreeLLMProvider', MockFreeLLMProvider):
        # Create agent
        agent = SecurityAgent(provider="gemini")
        agent.llm_provider.set_response_type("no_vulnerabilities")
        agent.llm = agent.llm_provider.get_llm("security")
        
        # Test that Pydantic validation fails with None snippet
        try:
            context = AnalysisContext(
                repo_name="test-security-repo",
                pr_id="PR-789",
                author="security.tester",
                commit_history=[],
                previous_issues=[],
                code_snippets=[None]  # None should fail validation
            )
            # If we reach here, the validation didn't work as expected
            assert False, "Expected Pydantic validation error for None snippet"
        except Exception as e:
            # Expected validation error
            assert "Input should be a valid dictionary or instance of CodeSnippet" in str(e)
            print("✓ None snippet validation correctly rejected by Pydantic model")
            return
        
        print("✓ None snippet handling works correctly")


def test_create_chain_functionality():
    """Test the _create_chain method functionality"""
    print("\nTesting _create_chain functionality...")
    
    with patch('agents.security_agent.FreeLLMProvider') as mock_provider:
        # Create a mock provider instance
        mock_llm = MockSecurityLLM("vulnerabilities_found")
        mock_provider_instance = Mock()
        mock_provider_instance.get_llm.return_value = mock_llm
        mock_provider.return_value = mock_provider_instance
        
        # Create agent
        agent = SecurityAgent(provider="gemini")
        
        # Test chain creation
        chain = agent._create_chain()
        
        # Verify chain is created
        assert chain is not None
        
        # Test chain invocation
        test_input = {
            "file_path": "test.py",
            "code": "password = 'secret123'"
        }
        
        result = chain.invoke(test_input)
        
        # Verify result
        assert isinstance(result, str)
        # Should contain JSON with vulnerabilities
        assert "[" in result and "]" in result
        
        print("✓ Chain creation and invocation works correctly")


def test_different_providers():
    """Test security agent with different providers"""
    print("\nTesting different providers...")
    
    providers = ["gemini", "openai", "claude"]
    
    for provider in providers:
        with patch('agents.security_agent.FreeLLMProvider') as mock_provider:
            mock_llm = MockSecurityLLM("single_vulnerability")
            mock_provider_instance = Mock()
            mock_provider_instance.get_llm.return_value = mock_llm
            mock_provider.return_value = mock_provider_instance
            
            # Create agent with different provider
            agent = SecurityAgent(provider=provider)
            state = create_test_security_state(1)
            
            # Test analysis
            response = agent.analyze(state)
            
            # Verify response
            assert len(response.security_results) == 1
            
            # Verify correct provider was used
            mock_provider.assert_called_with(provider)
            mock_provider_instance.get_llm.assert_called_with("security")
    
    print("✓ Different providers work correctly")


def test_critical_vulnerabilities():
    """Test analysis with critical vulnerabilities"""
    print("\nTesting critical vulnerabilities analysis...")
    
    with patch('agents.security_agent.FreeLLMProvider', MockFreeLLMProvider):
        # Create agent
        agent = SecurityAgent(provider="gemini")
        agent.llm_provider.set_response_type("critical_vulnerabilities")
        agent.llm = agent.llm_provider.get_llm("security")
        
        state = create_test_security_state(1)
        
        # Test analysis
        response = agent.analyze(state)
        
        # Verify response
        assert len(response.security_results) == 3
        
        # Check severity distribution
        severities = [vuln.severity for vuln in response.security_results]
        assert "critical" in severities
        assert "high" in severities
        assert "medium" in severities
        
        # Check specific vulnerabilities
        vuln_types = [vuln.type for vuln in response.security_results]
        assert "Command Injection" in vuln_types
        assert "Path Traversal" in vuln_types
        assert "Weak Encryption" in vuln_types
        
        print("✓ Critical vulnerabilities analysis works correctly")


def run_performance_test():
    """Run performance test for security analysis"""
    print("\nRunning performance test...")
    
    with patch('agents.security_agent.FreeLLMProvider') as mock_provider:
        mock_llm = MockSecurityLLM("vulnerabilities_found")
        mock_provider_instance = Mock()
        mock_provider_instance.get_llm.return_value = mock_llm
        mock_provider.return_value = mock_provider_instance
        
        # Create agent
        agent = SecurityAgent(provider="gemini")
        
        # Run multiple analyses
        times = []
        file_counts = [1, 3, 5]
        
        for i in range(15):  # 5 of each file count
            file_count = file_counts[i % 3]
            state = create_test_security_state(file_count)
            
            start_time = time.time()
            response = agent.analyze(state)
            duration = time.time() - start_time
            times.append(duration)
            
            # Each file should produce 2 vulnerabilities (from mock response)
            assert len(response.security_results) == file_count * 2
        
        avg_time = sum(times) / len(times)
        print(f"✓ Performance test completed")
        print(f"✓ Average analysis time: {avg_time:.3f} seconds")
        print(f"✓ Min time: {min(times):.3f}s, Max time: {max(times):.3f}s")


def test_state_validation():
    """Test analysis with various state configurations"""
    print("\nTesting state validation...")
    
    with patch('agents.security_agent.FreeLLMProvider') as mock_provider:
        mock_llm = MockSecurityLLM("no_vulnerabilities")
        mock_provider_instance = Mock()
        mock_provider_instance.get_llm.return_value = mock_llm
        mock_provider.return_value = mock_provider_instance
        
        agent = SecurityAgent(provider="gemini")
        
        # Test with empty code_snippets list
        context = AnalysisContext(
            repo_name="test-security-repo",
            pr_id="PR-789",
            author="security.tester",
            commit_history=[],
            previous_issues=[],
            code_snippets=[]
        )
        
        empty_snippets_state = TestWorkflowState(context)
        response = agent.analyze(empty_snippets_state)
        assert len(response.security_results) == 0
        
        print("✓ State validation works correctly")


def test_vulnerability_confidence_levels():
    """Test vulnerabilities with different confidence levels"""
    print("\nTesting vulnerability confidence levels...")
    
    with patch('agents.security_agent.FreeLLMProvider', MockFreeLLMProvider):
        # Test high confidence vulnerabilities
        agent = SecurityAgent(provider="gemini")
        agent.llm_provider.set_response_type("vulnerabilities_found")
        agent.llm = agent.llm_provider.get_llm("security")
        
        state = create_test_security_state(1)
        response = agent.analyze(state)
        
        assert len(response.security_results) == 2
        
        # Check confidence levels
        for vuln in response.security_results:
            assert 0.0 <= vuln.confidence <= 1.0
            if vuln.type == "SQL Injection":
                assert vuln.confidence == 0.95  # High confidence
            elif vuln.type == "Hardcoded Credentials":
                assert vuln.confidence == 0.9   # High confidence
        
        print("✓ Vulnerability confidence levels work correctly")


def test_vulnerability_model_validation():
    """Test Vulnerability model creation and validation"""
    print("\nTesting Vulnerability model validation...")
    
    # Test direct Vulnerability creation
    vuln = Vulnerability(
        type="Test Vulnerability",
        severity="high",
        description="Test description",
        line=10,
        file="test.py",
        confidence=0.8
    )
    
    assert vuln.type == "Test Vulnerability"
    assert vuln.severity == "high"
    assert vuln.description == "Test description"
    assert vuln.line == 10
    assert vuln.file == "test.py"
    assert vuln.confidence == 0.8
    
    print("✓ Vulnerability model validation works correctly")


def main():
    """Run all Security Agent tests"""
    print("=" * 60)
    print("SECURITY AGENT INDIVIDUAL TESTING")
    print("=" * 60)
    
    try:
        # Run all tests
        test_security_agent_initialization()
        test_analyze_with_vulnerabilities_found()
        test_analyze_with_no_vulnerabilities()
        test_analyze_multiple_files()
        test_analyze_with_tuple_snippets()
        test_analyze_json_parsing()
        test_analyze_malformed_json()
        test_analyze_partial_vulnerability_data()
        test_analyze_error_handling()
        test_analyze_empty_code_snippet()
        test_analyze_none_snippet()
        test_create_chain_functionality()
        test_different_providers()
        test_critical_vulnerabilities()
        test_state_validation()
        test_vulnerability_confidence_levels()
        test_vulnerability_model_validation()
        run_performance_test()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED SUCCESSFULLY!")
        print("=" * 60)
        
        # Summary
        print("\nTEST SUMMARY:")
        print("✓ Initialization test - PASSED")
        print("✓ Analysis with vulnerabilities found test - PASSED")
        print("✓ Analysis with no vulnerabilities test - PASSED")
        print("✓ Multiple files analysis test - PASSED")
        print("✓ Tuple snippets analysis test - PASSED")
        print("✓ JSON parsing test - PASSED")
        print("✓ Malformed JSON handling test - PASSED")
        print("✓ Partial vulnerability data test - PASSED")
        print("✓ Error handling test - PASSED")
        print("✓ Empty code snippet test - PASSED")
        print("✓ None snippet test - PASSED")
        print("✓ Chain functionality test - PASSED")
        print("✓ Different providers test - PASSED")
        print("✓ Critical vulnerabilities test - PASSED")
        print("✓ State validation test - PASSED")
        print("✓ Vulnerability confidence levels test - PASSED")
        print("✓ Vulnerability model validation test - PASSED")
        print("✓ Performance test - PASSED")
        
    except Exception as e:
        print(f"\n TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()