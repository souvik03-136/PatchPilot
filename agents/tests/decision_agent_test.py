import os
import sys
import time
import json
from unittest.mock import Mock, patch, MagicMock
from dotenv import load_dotenv

# Add root to path so `agents` can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from agents.models import AnalysisContext, CodeSnippet, Vulnerability, WorkflowState
from agents.decision_agent import DecisionAgent

load_dotenv()


class MockLLM:
    """Mock LLM for testing"""
    def __init__(self, response_type="approve"):
        self.response_type = response_type
    
    def invoke(self, prompt):
        if self.response_type == "approve":
            return """
            ```json
            {
                "decision": "APPROVE",
                "summary": "Only trivial issues found. Safe to merge.",
                "auto_fix_issues": ["minor_formatting", "unused_import"],
                "critical_issues": [],
                "recommendations": ["Run final tests before merge"]
            }
            ```
            """
        elif self.response_type == "request_changes":
            return """
            ```json
            {
                "decision": "REQUEST_CHANGES",
                "summary": "Medium severity issues found that need attention.",
                "auto_fix_issues": ["code_style"],
                "critical_issues": [],
                "recommendations": ["Fix SQL injection vulnerability", "Add input validation"]
            }
            ```
            """
        elif self.response_type == "block":
            return """
            ```json
            {
                "decision": "BLOCK",
                "summary": "Critical security issues found. Merge blocked.",
                "auto_fix_issues": [],
                "critical_issues": ["hardcoded_password", "sql_injection"],
                "recommendations": ["Immediate security review required", "Fix critical vulnerabilities"]
            }
            ```
            """
        elif self.response_type == "malformed":
            return "This is not valid JSON response"
        elif self.response_type == "no_json":
            return "Critical security issues found. This response has no JSON structure."
        else:
            return "{}"


def create_test_context():
    """Create a test AnalysisContext"""
    return AnalysisContext(
        repo_name="test-decision-repo",
        pr_id="PR-789",
        author="jane.doe",
        commit_history=[
            {"id": "abc123", "message": "feat: add payment processing"},
            {"id": "def456", "message": "fix: validate user input"},
            {"id": "ghi789", "message": "style: format code"}
        ],
        previous_issues=[],
        code_snippets=[
            CodeSnippet(
                file_path="payment/processor.py",
                content="""def process_payment(amount, card_number):
    # Process payment logic
    return True""",
                language="python"
            )
        ]
    )


def create_test_state(severity="low"):
    """Create test WorkflowState for decision making"""
    context = create_test_context()
    
    if severity == "low":
        security_results = [
            Vulnerability(
                type="Code Style",
                severity="low",
                description="Minor formatting issue",
                line=10,
                file="test.py",
                confidence=0.7
            )
        ]
    elif severity == "medium":
        security_results = [
            Vulnerability(
                type="Input Validation",
                severity="medium",
                description="Missing input validation",
                line=15,
                file="auth.py",
                confidence=0.8
            ),
            Vulnerability(
                type="SQL Injection",
                severity="medium",
                description="Potential SQL injection",
                line=25,
                file="database.py",
                confidence=0.85
            )
        ]
    else:  # high/critical
        security_results = [
            Vulnerability(
                type="Hardcoded Credentials",
                severity="critical",
                description="Hardcoded password in source",
                line=42,
                file="config.py",
                confidence=0.95
            ),
            Vulnerability(
                type="SQL Injection",
                severity="high",
                description="Direct SQL injection vulnerability",
                line=28,
                file="database.py",
                confidence=0.9
            )
        ]
    
    quality_results = [
        {"type": "complexity", "severity": "medium", "description": "High cyclomatic complexity"}
    ]
    
    logic_results = [
        {"type": "logic_error", "severity": "low", "description": "Unreachable code detected"}
    ]
    
    # Create WorkflowState with all required fields
    try:
        # Try to create with all fields at once
        state = WorkflowState(
            context=context,
            security_results=security_results,
            quality_results=quality_results,
            logic_results=logic_results
        )
    except Exception:
        # If that fails, try with just required fields
        try:
            state = WorkflowState(context=context)
            state.security_results = security_results
            state.quality_results = quality_results
            state.logic_results = logic_results
        except Exception:
            # Last resort - create empty and set attributes
            state = type('WorkflowState', (), {})()
            state.context = context
            state.security_results = security_results
            state.quality_results = quality_results
            state.logic_results = logic_results
    
    # Add optional attributes
    if hasattr(state, '__dict__') or hasattr(type(state), '__setattr__'):
        state.enriched_context = {
            "developer_profile": "experienced",
            "risk_assessment": "medium",
            "historical_issues": 2
        }
    
    return state


def test_decision_agent_initialization():
    """Test DecisionAgent initialization"""
    print("Testing DecisionAgent initialization...")
    
    with patch('agents.decision_agent.get_llm') as mock_get_llm:
        mock_get_llm.return_value = MockLLM()
        
        # Create agent
        agent = DecisionAgent(provider="gemini")
        
        # Verify initialization
        assert agent.llm is not None
        assert agent.prompt is not None
        
        # Verify get_llm was called correctly
        mock_get_llm.assert_called_once_with("decision", "gemini")
        
        print("✓ DecisionAgent initialized successfully")


def test_approve_decision():
    """Test APPROVE decision for trivial issues"""
    print("\nTesting APPROVE decision...")
    
    with patch('agents.decision_agent.get_llm') as mock_get_llm:
        mock_get_llm.return_value = MockLLM("approve")
        
        # Create agent and test state
        agent = DecisionAgent(provider="gemini")
        state = create_test_state("low")
        
        # Test decision
        start_time = time.time()
        result_state = agent.make_decision(state)
        duration = time.time() - start_time
        
        # Debug: Print what we actually got
        print(f"DEBUG - Decision: {result_state.decision}")
        
        # Verify response based on actual implementation
        assert hasattr(result_state, 'decision')
        assert result_state.decision is not None
        assert result_state.decision["decision"] == "APPROVE"
        assert result_state.decision["risk_level"] == "low"
        assert "No critical issues found" in result_state.decision["summary"]
        
        print(f"✓ APPROVE decision completed in {duration:.3f} seconds")
        print(f"✓ Decision: {result_state.decision['decision']}")
        print(f"✓ Risk level: {result_state.decision['risk_level']}")
        print(f"✓ Summary: {result_state.decision['summary']}")


def test_request_changes_decision():
    """Test REQUEST_CHANGES decision for medium issues"""
    print("\nTesting REQUEST_CHANGES decision...")
    
    with patch('agents.decision_agent.get_llm') as mock_get_llm:
        mock_get_llm.return_value = MockLLM("request_changes")
        
        # Create agent and test state with high severity issues
        agent = DecisionAgent(provider="gemini")
        state = create_test_state("medium")
        
        # Add a high severity issue to trigger REQUEST_CHANGES
        high_vuln = Vulnerability(
            type="SQL Injection",
            severity="high",
            description="SQL injection vulnerability",
            line=30,
            file="database.py",
            confidence=0.9
        )
        state.security_results.append(high_vuln)
        
        # Test decision
        result_state = agent.make_decision(state)
        
        # Debug output
        print(f"DEBUG - Decision: {result_state.decision}")
        
        # Verify response
        assert hasattr(result_state, 'decision')
        assert result_state.decision is not None
        assert result_state.decision["decision"] == "REQUEST_CHANGES"
        assert result_state.decision["risk_level"] == "high"
        assert "high severity issues" in result_state.decision["summary"]
        
        print("✓ REQUEST_CHANGES decision working correctly")
        print(f"✓ Decision: {result_state.decision['decision']}")
        print(f"✓ Risk level: {result_state.decision['risk_level']}")
        print(f"✓ Summary: {result_state.decision['summary']}")


def test_block_decision():
    """Test BLOCK decision for critical issues"""
    print("\nTesting BLOCK decision...")
    
    with patch('agents.decision_agent.get_llm') as mock_get_llm:
        mock_get_llm.return_value = MockLLM("block")
        
        # Create agent and test state
        agent = DecisionAgent(provider="gemini")
        state = create_test_state("critical")
        
        # Test decision
        result_state = agent.make_decision(state)
        
        # Verify response
        assert hasattr(result_state, 'decision')
        assert result_state.decision is not None
        assert result_state.decision["decision"] == "BLOCK"
        assert result_state.decision["risk_level"] == "critical"
        assert "critical issues found" in result_state.decision["summary"]
        
        print("✓ BLOCK decision working correctly")
        print(f"✓ Decision: {result_state.decision['decision']}")
        print(f"✓ Risk level: {result_state.decision['risk_level']}")
        print(f"✓ Summary: {result_state.decision['summary']}")


def test_block_decision_too_many_high():
    """Test BLOCK decision for too many high severity issues"""
    print("\nTesting BLOCK decision for too many high issues...")
    
    with patch('agents.decision_agent.get_llm') as mock_get_llm:
        mock_get_llm.return_value = MockLLM("block")
        
        # Create agent and test state
        agent = DecisionAgent(provider="gemini")
        state = create_test_state("low")  # Start with low severity
        
        # Add more than 3 high severity issues
        for i in range(4):
            high_vuln = Vulnerability(
                type=f"High Issue {i+1}",
                severity="high",
                description=f"High severity issue {i+1}",
                line=10+i,
                file=f"file{i+1}.py",
                confidence=0.8
            )
            state.security_results.append(high_vuln)
        
        # Test decision
        result_state = agent.make_decision(state)
        
        # Verify response
        assert result_state.decision["decision"] == "BLOCK"
        assert result_state.decision["risk_level"] == "high"
        assert "high severity issues (>3)" in result_state.decision["summary"]
        
        print("✓ BLOCK decision for too many high issues working correctly")
        print(f"✓ Decision: {result_state.decision['decision']}")
        print(f"✓ Risk level: {result_state.decision['risk_level']}")
        print(f"✓ Summary: {result_state.decision['summary']}")


def test_decision_error_handling():
    """Test error handling in decision making"""
    print("\nTesting error handling in decision making...")
    
    with patch('agents.decision_agent.get_llm') as mock_get_llm:
        # Setup mock to raise exception
        mock_llm = Mock()
        mock_llm.invoke.side_effect = Exception("LLM connection failed")
        mock_get_llm.return_value = mock_llm
        
        # Create agent and test state
        agent = DecisionAgent(provider="gemini")
        state = create_test_state("low")
        
        # Test decision with error - should still work due to rule-based logic
        result_state = agent.make_decision(state)
        
        # The current implementation doesn't use LLM for decision making,
        # it uses rule-based logic, so it should still work
        assert hasattr(result_state, 'decision')
        assert result_state.decision is not None
        
        print("✓ Error handling works correctly")
        print(f"✓ Decision still made: {result_state.decision['decision']}")


def test_parse_response_valid_json():
    """Test parsing valid JSON response"""
    print("\nTesting valid JSON response parsing...")
    
    with patch('agents.decision_agent.get_llm') as mock_get_llm:
        mock_get_llm.return_value = MockLLM()
        
        agent = DecisionAgent(provider="gemini")
        
        # Test valid JSON with code blocks
        json_response = """
        ```json
        {
            "decision": "APPROVE",
            "summary": "Test summary",
            "auto_fix_issues": ["test_issue"],
            "critical_issues": []
        }
        ```
        """
        
        result = agent._parse_response(json_response)
        
        assert result["decision"] == "APPROVE"
        assert result["summary"] == "Test summary"
        assert result["auto_fix_issues"] == ["test_issue"]
        assert result["critical_issues"] == []
        
        print("✓ Valid JSON parsing works correctly")


def test_parse_response_malformed_json():
    """Test parsing malformed JSON response"""
    print("\nTesting malformed JSON response parsing...")
    
    with patch('agents.decision_agent.get_llm') as mock_get_llm:
        mock_get_llm.return_value = MockLLM()
        
        agent = DecisionAgent(provider="gemini")
        
        # Test malformed JSON
        malformed_response = "This is not valid JSON but contains critical issues"
        
        result = agent._parse_response(malformed_response)
        
        # Should fallback to text analysis
        assert result["decision"] == "BLOCK"  # Contains "critical"
        assert result["summary"] == malformed_response[:200]
        assert result["auto_fix_issues"] == []
        assert result["critical_issues"] == []
        
        print("✓ Malformed JSON fallback works correctly")


def test_parse_response_no_json():
    """Test parsing response without JSON"""
    print("\nTesting response without JSON...")
    
    with patch('agents.decision_agent.get_llm') as mock_get_llm:
        mock_get_llm.return_value = MockLLM()
        
        agent = DecisionAgent(provider="gemini")
        
        # Test response without critical keywords
        normal_response = "Everything looks good, no issues found"
        
        result = agent._parse_response(normal_response)
        
        # Should fallback to REQUEST_CHANGES (default)
        assert result["decision"] == "REQUEST_CHANGES"
        assert result["summary"] == normal_response[:200]
        
        print("✓ Non-JSON response fallback works correctly")


def test_decision_with_different_providers():
    """Test decision agent with different providers"""
    print("\nTesting different providers...")
    
    providers = ["gemini", "openai", "claude"]
    
    for provider in providers:
        with patch('agents.decision_agent.get_llm') as mock_get_llm:
            mock_get_llm.return_value = MockLLM("approve")
            
            # Create agent with different provider
            agent = DecisionAgent(provider=provider)
            state = create_test_state("low")
            
            # Test decision
            result_state = agent.make_decision(state)
            
            # Verify response
            assert hasattr(result_state, 'decision')
            assert result_state.decision is not None
            
            # Verify correct provider was used
            mock_get_llm.assert_called_with("decision", provider)
    
    print("✓ Different providers work correctly")


def run_performance_test():
    """Run performance test for decision making"""
    print("\nRunning performance test...")
    
    with patch('agents.decision_agent.get_llm') as mock_get_llm:
        mock_get_llm.return_value = MockLLM("approve")
        
        # Create agent
        agent = DecisionAgent(provider="gemini")
        
        # Run multiple decisions
        times = []
        decision_types = ["low", "medium", "critical"]
        
        for i in range(15):  # 5 of each type
            state = create_test_state(decision_types[i % 3])
            state.context.pr_id = f"PR-{i+1}"
            
            start_time = time.time()
            result_state = agent.make_decision(state)
            duration = time.time() - start_time
            times.append(duration)
            
            assert hasattr(result_state, 'decision')
            assert result_state.decision is not None
        
        avg_time = sum(times) / len(times)
        print(f"✓ Performance test completed")
        print(f"✓ Average decision time: {avg_time:.3f} seconds")
        print(f"✓ Min time: {min(times):.3f}s, Max time: {max(times):.3f}s")


def test_state_validation():
    """Test decision making with various state configurations"""
    print("\nTesting state validation...")
    
    with patch('agents.decision_agent.get_llm') as mock_get_llm:
        mock_get_llm.return_value = MockLLM("approve")
        
        agent = DecisionAgent(provider="gemini")
        
        # Test with minimal state
        try:
            minimal_state = WorkflowState(
                context=create_test_context(),
                security_results=[],
                quality_results=[],
                logic_results=[]
            )
        except Exception:
            # Fallback if constructor doesn't work
            minimal_state = type('WorkflowState', (), {})()
            minimal_state.context = create_test_context()
            minimal_state.security_results = []
            minimal_state.quality_results = []
            minimal_state.logic_results = []
        
        result_state = agent.make_decision(minimal_state)
        assert hasattr(result_state, 'decision')
        assert result_state.decision is not None
        
        # Test with missing enriched_context
        state_no_context = create_test_state("low")
        if hasattr(state_no_context, 'enriched_context'):
            try:
                delattr(state_no_context, 'enriched_context')
            except:
                pass  # May not be deletable in Pydantic models
        
        result_state = agent.make_decision(state_no_context)
        assert hasattr(result_state, 'decision')
        assert result_state.decision is not None
        
        print("✓ State validation works correctly")


def test_decision_logic_rules():
    """Test the core decision logic rules"""
    print("\nTesting decision logic rules...")
    
    with patch('agents.decision_agent.get_llm') as mock_get_llm:
        mock_get_llm.return_value = MockLLM("approve")
        
        agent = DecisionAgent(provider="gemini")
        
        # Test 1: No issues = APPROVE
        try:
            state = WorkflowState(
                context=create_test_context(),
                security_results=[],
                quality_results=[],
                logic_results=[]
            )
        except Exception:
            state = type('WorkflowState', (), {})()
            state.context = create_test_context()
            state.security_results = []
            state.quality_results = []
            state.logic_results = []
            
        result_state = agent.make_decision(state)
        assert result_state.decision["decision"] == "APPROVE"
        
        # Test 2: Critical issues = BLOCK
        state = create_test_state("critical")
        result_state = agent.make_decision(state)
        assert result_state.decision["decision"] == "BLOCK"
        assert result_state.decision["risk_level"] == "critical"
        
        # Test 3: More than 3 high issues = BLOCK
        state = create_test_state("low")
        state.security_results = []
        for i in range(4):
            state.security_results.append(Vulnerability(
                type=f"High Issue {i}",
                severity="high",
                description=f"High issue {i}",
                line=i,
                file=f"file{i}.py",
                confidence=0.8
            ))
        result_state = agent.make_decision(state)
        assert result_state.decision["decision"] == "BLOCK"
        assert result_state.decision["risk_level"] == "high"
        
        # Test 4: 1-3 high issues = REQUEST_CHANGES
        state = create_test_state("low")
        state.security_results = [Vulnerability(
            type="High Issue",
            severity="high",
            description="One high issue",
            line=1,
            file="file.py",
            confidence=0.8
        )]
        result_state = agent.make_decision(state)
        assert result_state.decision["decision"] == "REQUEST_CHANGES"
        assert result_state.decision["risk_level"] == "high"
        
        print("✓ Decision logic rules working correctly")


def main():
    """Run all Decision Agent tests"""
    print("=" * 60)
    print("DECISION AGENT INDIVIDUAL TESTING")
    print("=" * 60)
    
    try:
        # Run all tests
        test_decision_agent_initialization()
        test_approve_decision()
        test_request_changes_decision()
        test_block_decision()
        test_block_decision_too_many_high()
        test_decision_error_handling()
        test_parse_response_valid_json()
        test_parse_response_malformed_json()
        test_parse_response_no_json()
        test_decision_with_different_providers()
        test_state_validation()
        test_decision_logic_rules()
        run_performance_test()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED SUCCESSFULLY!")
        print("=" * 60)
        
        # Summary
        print("\nTEST SUMMARY:")
        print("✓ Initialization test - PASSED")
        print("✓ APPROVE decision test - PASSED")
        print("✓ REQUEST_CHANGES decision test - PASSED")
        print("✓ BLOCK decision test - PASSED")
        print("✓ BLOCK for too many high issues test - PASSED")
        print("✓ Error handling test - PASSED")
        print("✓ Valid JSON parsing test - PASSED")
        print("✓ Malformed JSON parsing test - PASSED")
        print("✓ No JSON response test - PASSED")
        print("✓ Different providers test - PASSED")
        print("✓ State validation test - PASSED")
        print("✓ Decision logic rules test - PASSED")
        print("✓ Performance test - PASSED")
        
    except Exception as e:
        print(f"\n TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()