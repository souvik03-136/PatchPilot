import os
import sys
import time
import json
from unittest.mock import Mock, patch, MagicMock
from dotenv import load_dotenv

# Add root to path so `agents` can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from agents.models import AnalysisContext, CodeSnippet, Vulnerability, AgentResponse
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


def mock_generate_patch(issue, context):
    """Mock patch generation function"""
    print(f"DEBUG - Generating patch for issue: '{issue}'")
    if issue in ["minor_formatting", "unused_import", "code_style"]:
        patch = {
            "file": "test_file.py",
            "patch": f"- # Fix for {issue}",
            "description": f"Auto-fix for {issue}",
            "type": "auto_fix"
        }
        print(f"DEBUG - Generated patch: {patch}")
        return patch
    print(f"DEBUG - No patch generated for issue: '{issue}'")
    return None


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
    """Create test state for decision making"""
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
    
    return {
        "context": context,
        "security_results": security_results,
        "quality_results": [
            {"type": "complexity", "severity": "medium", "description": "High cyclomatic complexity"}
        ],
        "logic_results": [
            {"type": "logic_error", "severity": "low", "description": "Unreachable code detected"}
        ],
        "enriched_context": {
            "developer_profile": "experienced",
            "risk_assessment": "medium",
            "historical_issues": 2
        }
    }


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
    
    with patch('agents.decision_agent.get_llm') as mock_get_llm, \
         patch('agents.decision_agent.generate_patch', side_effect=mock_generate_patch):
        
        mock_get_llm.return_value = MockLLM("approve")
        
        # Create agent and test state
        agent = DecisionAgent(provider="gemini")
        state = create_test_state("low")
        
        # Test decision
        start_time = time.time()
        response = agent.make_decision(state)
        duration = time.time() - start_time
        
        # Debug: Print what we actually got
        print(f"DEBUG - Response success: {response.success}")
        print(f"DEBUG - Response results: {response.results}")
        print(f"DEBUG - Response metadata: {response.metadata}")
        print(f"DEBUG - Response errors: {response.errors}")
        
        # Verify response
        assert response.success == True
        assert len(response.results) == 1
        assert response.results[0]["decision"] == "APPROVE"
        
        # Check if patches exist in metadata
        patches_count = len(response.metadata.get("patches", []))
        print(f"DEBUG - Patches count: {patches_count}")
        
        # For APPROVE decision, we expect patches to be generated for auto_fix_issues
        # The mock LLM returns ["minor_formatting", "unused_import"] which should generate 2 patches
        expected_patches = 2
        assert patches_count == expected_patches, f"Expected {expected_patches} patches, got {patches_count}"
        assert response.errors == []
        
        print(f"✓ APPROVE decision completed in {duration:.3f} seconds")
        print(f"✓ Decision: {response.results[0]['decision']}")
        print(f"✓ Patches generated: {patches_count}")
        print(f"✓ Summary: {response.results[0]['summary']}")


def test_request_changes_decision():
    """Test REQUEST_CHANGES decision for medium issues"""
    print("\nTesting REQUEST_CHANGES decision...")
    
    with patch('agents.decision_agent.get_llm') as mock_get_llm, \
         patch('agents.decision_agent.generate_patch', side_effect=mock_generate_patch):
        
        mock_get_llm.return_value = MockLLM("request_changes")
        
        # Create agent and test state
        agent = DecisionAgent(provider="gemini")
        state = create_test_state("medium")
        
        # Test decision
        response = agent.make_decision(state)
        
        # Debug output
        print(f"DEBUG - Response success: {response.success}")
        print(f"DEBUG - Response results: {response.results}")
        print(f"DEBUG - Response metadata: {response.metadata}")
        print(f"DEBUG - Auto fix issues: {response.results[0].get('auto_fix_issues', [])}")
        
        # Verify response
        assert response.success == True
        assert len(response.results) == 1
        assert response.results[0]["decision"] == "REQUEST_CHANGES"
        
        # The mock LLM returns ["code_style"] which should generate 1 patch
        expected_patches = 1
        actual_patches = len(response.metadata.get("patches", []))
        assert actual_patches == expected_patches, f"Expected {expected_patches} patches, got {actual_patches}"
        assert response.errors == []
        
        print("✓ REQUEST_CHANGES decision working correctly")
        print(f"✓ Decision: {response.results[0]['decision']}")
        print(f"✓ Patches generated: {len(response.metadata.get('patches', []))}")
        print(f"✓ Recommendations: {response.results[0]['recommendations']}")


def test_block_decision():
    """Test BLOCK decision for critical issues"""
    print("\nTesting BLOCK decision...")
    
    with patch('agents.decision_agent.get_llm') as mock_get_llm, \
         patch('agents.decision_agent.generate_patch', side_effect=mock_generate_patch):
        
        mock_get_llm.return_value = MockLLM("block")
        
        # Create agent and test state
        agent = DecisionAgent(provider="gemini")
        state = create_test_state("critical")
        
        # Test decision
        response = agent.make_decision(state)
        
        # Verify response
        assert response.success == True
        assert len(response.results) == 1
        assert response.results[0]["decision"] == "BLOCK"
        assert len(response.metadata.get("patches", [])) == 0  # No auto-fixes for critical issues
        assert len(response.metadata["critical_issues"]) == 2
        assert response.errors == []
        
        print("✓ BLOCK decision working correctly")
        print(f"✓ Decision: {response.results[0]['decision']}")
        print(f"✓ Critical issues: {len(response.metadata['critical_issues'])}")
        print(f"✓ Summary: {response.results[0]['summary']}")


def test_decision_error_handling():
    """Test error handling in decision making"""
    print("\nTesting error handling in decision making...")
    
    with patch('agents.decision_agent.get_llm') as mock_get_llm, \
         patch('agents.decision_agent.generate_patch', side_effect=mock_generate_patch):
        
        # Setup mock to raise exception
        mock_llm = Mock()
        mock_llm.invoke.side_effect = Exception("LLM connection failed")
        mock_get_llm.return_value = mock_llm
        
        # Create agent and test state
        agent = DecisionAgent(provider="gemini")
        state = create_test_state("low")
        
        # Test decision with error
        response = agent.make_decision(state)
        
        # Verify error handling
        assert response.success == False
        assert len(response.errors) > 0
        assert "Decision failed" in response.errors[0] or "LLM connection failed" in response.errors[0]
        assert response.results == []
        
        print("✓ Error handling works correctly")
        print(f"✓ Response success: {response.success}")
        print(f"✓ Error message: {response.errors[0]}")


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


def test_patch_generation_integration():
    """Test patch generation integration"""
    print("\nTesting patch generation integration...")
    
    with patch('agents.decision_agent.get_llm') as mock_get_llm, \
         patch('agents.decision_agent.generate_patch', side_effect=mock_generate_patch):
        
        mock_get_llm.return_value = MockLLM("approve")
        
        # Create agent and test state
        agent = DecisionAgent(provider="gemini")
        state = create_test_state("low")
        
        # Test decision
        response = agent.make_decision(state)
        
        # Verify patches - APPROVE mock returns ["minor_formatting", "unused_import"]
        expected_patches = 2
        actual_patches = len(response.metadata.get("patches", []))
        assert actual_patches == expected_patches, f"Expected {expected_patches} patches, got {actual_patches}"
        
        for generated_patch in response.metadata.get("patches", []):
            assert "file" in generated_patch
            assert "patch" in generated_patch
            assert "description" in generated_patch
            assert "type" in generated_patch
            assert generated_patch["type"] == "auto_fix"
        
        print("✓ Patch generation integration works correctly")
        print(f"✓ Patches generated: {len(response.metadata.get('patches', []))}")


def test_decision_with_different_providers():
    """Test decision agent with different providers"""
    print("\nTesting different providers...")
    
    providers = ["gemini", "openai", "claude"]
    
    for provider in providers:
        with patch('agents.decision_agent.get_llm') as mock_get_llm, \
             patch('agents.decision_agent.generate_patch', side_effect=mock_generate_patch):
            
            mock_get_llm.return_value = MockLLM("approve")
            
            # Create agent with different provider
            agent = DecisionAgent(provider=provider)
            state = create_test_state("low")
            
            # Test decision
            response = agent.make_decision(state)
            
            # Verify response
            assert response.success == True
            assert len(response.results) == 1
            
            # Verify correct provider was used
            mock_get_llm.assert_called_with("decision", provider)
    
    print("✓ Different providers work correctly")


def run_performance_test():
    """Run performance test for decision making"""
    print("\nRunning performance test...")
    
    with patch('agents.decision_agent.get_llm') as mock_get_llm, \
         patch('agents.decision_agent.generate_patch', side_effect=mock_generate_patch):
        
        mock_get_llm.return_value = MockLLM("approve")
        
        # Create agent
        agent = DecisionAgent(provider="gemini")
        
        # Run multiple decisions
        times = []
        decision_types = ["low", "medium", "critical"]
        
        for i in range(15):  # 5 of each type
            state = create_test_state(decision_types[i % 3])
            state["context"].pr_id = f"PR-{i+1}"
            
            start_time = time.time()
            response = agent.make_decision(state)
            duration = time.time() - start_time
            times.append(duration)
            
            assert response.success == True
        
        avg_time = sum(times) / len(times)
        print(f"✓ Performance test completed")
        print(f"✓ Average decision time: {avg_time:.3f} seconds")
        print(f"✓ Min time: {min(times):.3f}s, Max time: {max(times):.3f}s")


def test_state_validation():
    """Test decision making with various state configurations"""
    print("\nTesting state validation...")
    
    with patch('agents.decision_agent.get_llm') as mock_get_llm, \
         patch('agents.decision_agent.generate_patch', side_effect=mock_generate_patch):
        
        mock_get_llm.return_value = MockLLM("approve")
        
        agent = DecisionAgent(provider="gemini")
        
        # Test with minimal state
        minimal_state = {
            "context": create_test_context(),
            "security_results": [],
            "quality_results": [],
            "logic_results": []
        }
        
        response = agent.make_decision(minimal_state)
        assert response.success == True
        
        # Test with missing enriched_context
        state_no_context = create_test_state("low")
        del state_no_context["enriched_context"]
        
        response = agent.make_decision(state_no_context)
        assert response.success == True
        
        print("✓ State validation works correctly")


def test_debug_patch_generation():
    """Test patch generation with detailed debugging"""
    print("\nTesting patch generation with debugging...")
    
    with patch('agents.decision_agent.get_llm') as mock_get_llm, \
         patch('agents.decision_agent.generate_patch', side_effect=mock_generate_patch):
        
        mock_get_llm.return_value = MockLLM("approve")
        
        # Create agent and test state
        agent = DecisionAgent(provider="gemini")
        state = create_test_state("low")
        
        # Test decision
        response = agent.make_decision(state)
        
        # Debug information
        print(f"✓ LLM Response auto_fix_issues: {response.results[0].get('auto_fix_issues', [])}")
        print(f"✓ Patches in metadata: {len(response.metadata.get('patches', []))}")
        print(f"✓ Patches details: {response.metadata.get('patches', [])}")
        
        # Verify that the patch generation function was called
        # This test helps us understand what's happening
        assert response.success == True
        
        print("✓ Debug patch generation test completed")


def main():
    """Run all Decision Agent tests"""
    print("=" * 60)
    print("DECISION AGENT INDIVIDUAL TESTING")
    print("=" * 60)
    
    try:
        # Run all tests
        test_decision_agent_initialization()
        test_debug_patch_generation()  # Add this first to debug
        test_approve_decision()
        test_request_changes_decision()
        test_block_decision()
        test_decision_error_handling()
        test_parse_response_valid_json()
        test_parse_response_malformed_json()
        test_parse_response_no_json()
        test_patch_generation_integration()
        test_decision_with_different_providers()
        test_state_validation()
        run_performance_test()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED SUCCESSFULLY!")
        print("=" * 60)
        
        # Summary
        print("\nTEST SUMMARY:")
        print("✓ Initialization test - PASSED")
        print("✓ Debug patch generation test - PASSED")
        print("✓ APPROVE decision test - PASSED")
        print("✓ REQUEST_CHANGES decision test - PASSED")
        print("✓ BLOCK decision test - PASSED")
        print("✓ Error handling test - PASSED")
        print("✓ Valid JSON parsing test - PASSED")
        print("✓ Malformed JSON parsing test - PASSED")
        print("✓ No JSON response test - PASSED")
        print("✓ Patch generation integration test - PASSED")
        print("✓ Different providers test - PASSED")
        print("✓ State validation test - PASSED")
        print("✓ Performance test - PASSED")
        
    except Exception as e:
        print(f"\n TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()