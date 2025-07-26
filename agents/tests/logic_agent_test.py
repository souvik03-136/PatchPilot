import os
import sys
import time
import json
from unittest.mock import Mock, patch, MagicMock
from dotenv import load_dotenv

# Add root to path so `agents` can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from agents.models import AnalysisContext, CodeSnippet, AgentResponse
from agents.logic_agent import LogicAgent

load_dotenv()


from langchain_core.runnables.base import Runnable
from langchain_core.runnables.utils import Input, Output


class MockWorkflowState:
    """Mock WorkflowState for testing"""
    def __init__(self, context, code_snippets=None):
        self.context = context
        if code_snippets:
            self.context.code_snippets = code_snippets
        self.logic_results = []
        self.logic_errors = []


class MockLLM(Runnable):
    """Mock LLM for testing that implements LangChain's Runnable interface"""
    
    def __init__(self, response_type="issues_found"):
        self.response_type = response_type
        super().__init__()
    
    def invoke(self, input: Input, config=None, **kwargs) -> Output:
        if self.response_type == "issues_found":
            return """
## Logic Analysis for test_file.py

### Issues Found:
1. **Null Pointer Exception**: Variable 'user' could be null
   - Line: 15
   - Severity: High
   - Fix: Add null check before accessing user properties

2. **Race Condition**: Shared variable access without synchronization
   - Line: 25
   - Severity: Medium
   - Fix: Use proper locking mechanism

### Suggestions:
- Add input validation for all user inputs
- Implement proper error handling
"""
        elif self.response_type == "no_issues":
            return """
## Logic Analysis for clean_file.py

No logic issues detected.

The code follows best practices and handles edge cases properly.
"""
        elif self.response_type == "complex_issues":
            return """
## Logic Analysis for complex_file.py

### Issues Found:
1. **Infinite Loop**: Loop condition never changes
   - Line: 42
   - Severity: High
   - Fix: Update loop variable inside the loop

2. **Memory Leak**: Resources not properly released
   - Line: 18
   - Severity: High
   - Fix: Use try-with-resources or proper cleanup

3. **API Contract Violation**: Method returns null instead of empty collection
   - Line: 55
   - Severity: Medium
   - Fix: Return empty list instead of null

4. **Edge Case Handling**: Division by zero not handled
   - Line: 30
   - Severity: Medium
   - Fix: Check for zero before division

### Suggestions:
- Implement comprehensive unit tests
- Add logging for debugging
- Use defensive programming practices
"""
        elif self.response_type == "malformed":
            return "This is a malformed response without proper structure"
        elif self.response_type == "exception":
            raise Exception("LLM connection failed")
        else:
            return "## Logic Analysis\n\nGeneric analysis response"
    
    async def ainvoke(self, input: Input, config=None, **kwargs) -> Output:
        return self.invoke(input, config, **kwargs)
    
    def batch(self, inputs, config=None, **kwargs):
        return [self.invoke(inp, config, **kwargs) for inp in inputs]
    
    async def abatch(self, inputs, config=None, **kwargs):
        return [await self.ainvoke(inp, config, **kwargs) for inp in inputs]
    
    def stream(self, input: Input, config=None, **kwargs):
        yield self.invoke(input, config, **kwargs)
    
    async def astream(self, input: Input, config=None, **kwargs):
        yield self.invoke(input, config, **kwargs)


class MockFreeLLMProvider:
    """Mock FreeLLMProvider for testing"""
    def __init__(self, provider):
        self.provider = provider
        self.mock_llm = None
    
    def set_response_type(self, response_type):
        self.mock_llm = MockLLM(response_type)
    
    def get_llm(self, agent_type):
        if self.mock_llm is None:
            self.mock_llm = MockLLM()
        return self.mock_llm


def mock_parse_code_blocks(text):
    """Mock parse_code_blocks function"""
    # Extract suggestions from the analysis text
    suggestions = []
    if "suggestions:" in text.lower():
        lines = text.split('\n')
        in_suggestions = False
        for line in lines:
            if "suggestions:" in line.lower():
                in_suggestions = True
                continue
            if in_suggestions and line.strip().startswith('-'):
                suggestions.append(line.strip()[1:].strip())
    return suggestions


def create_test_code_snippets():
    """Create test code snippets"""
    return [
        CodeSnippet(
            file_path="test_file.py",
            content="""def process_user(user_id):
    user = get_user(user_id)
    if user:
        return user.name
    return None""",
            language="python"
        ),
        CodeSnippet(
            file_path="clean_file.py",
            content="""def add_numbers(a, b):
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise ValueError("Both arguments must be numbers")
    return a + b""",
            language="python"
        ),
        CodeSnippet(
            file_path="complex_file.py",
            content="""def complex_function(data):
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result""",
            language="python"
        )
    ]


def create_test_state(snippet_count=1):
    """Create test state for logic analysis"""
    snippets = create_test_code_snippets()[:snippet_count]
    context = AnalysisContext(
        repo_name="test-logic-repo",
        pr_id="PR-456",
        author="john.doe",
        commit_history=[
            {"id": "abc123", "message": "feat: add user processing"},
            {"id": "def456", "message": "fix: handle edge cases"}
        ],
        previous_issues=[],
        code_snippets=snippets
    )
    return MockWorkflowState(context)


def test_logic_agent_initialization():
    """Test LogicAgent initialization"""
    print("Testing LogicAgent initialization...")
    
    with patch('agents.logic_agent.FreeLLMProvider', MockFreeLLMProvider):
        # Create agent
        agent = LogicAgent(provider="gemini")
        
        # Verify initialization
        assert agent.llm is not None
        assert agent.parser is not None
        assert agent.prompt is not None
        assert agent.llm_provider is not None
        assert isinstance(agent.llm, MockLLM)
        
        print("✓ LogicAgent initialized successfully")


def test_logic_agent_initialization_with_custom_llm():
    """Test LogicAgent initialization with custom LLM"""
    print("\nTesting LogicAgent initialization with custom LLM...")
    
    custom_llm = MockLLM()
    agent = LogicAgent(llm=custom_llm)
    
    # Verify initialization
    assert agent.llm is custom_llm
    assert agent.parser is not None
    assert agent.prompt is not None
    assert not hasattr(agent, 'llm_provider')  # Should not have provider when custom LLM provided
    
    print("✓ LogicAgent initialized with custom LLM successfully")


def test_analyze_with_issues_found():
    """Test logic analysis when issues are found"""
    print("\nTesting logic analysis with issues found...")
    
    with patch('agents.logic_agent.FreeLLMProvider', MockFreeLLMProvider), \
         patch('agents.logic_agent.parse_code_blocks', side_effect=mock_parse_code_blocks):
        
        # Create agent and test state
        agent = LogicAgent(provider="gemini")
        agent.llm_provider.set_response_type("issues_found")
        agent.llm = agent.llm_provider.get_llm("logic")
        
        state = create_test_state(1)
        
        # Test analysis
        start_time = time.time()
        result_state = agent.analyze(state)
        duration = time.time() - start_time
        
        # Debug: Print what we actually got
        print(f"DEBUG - Logic results count: {len(result_state.logic_results)}")
        print(f"DEBUG - Logic errors: {result_state.logic_errors}")
        
        # Verify response
        assert len(result_state.logic_results) == 1
        assert len(result_state.logic_errors) == 0
        
        # Check first result
        result = result_state.logic_results[0]
        assert result["file"] == "test_file.py"
        assert result["has_issues"] == True
        assert "null pointer exception" in result["analysis"].lower()
        assert "race condition" in result["analysis"].lower()
        assert isinstance(result["suggestions"], list)
        
        print(f"✓ Logic analysis with issues completed in {duration:.3f} seconds")
        print(f"✓ Issues detected: {result['has_issues']}")
        print(f"✓ File analyzed: {result['file']}")


def test_analyze_with_no_issues():
    """Test logic analysis when no issues are found"""
    print("\nTesting logic analysis with no issues...")
    
    with patch('agents.logic_agent.FreeLLMProvider', MockFreeLLMProvider), \
         patch('agents.logic_agent.parse_code_blocks', side_effect=mock_parse_code_blocks):
        
        # Create agent and test state
        agent = LogicAgent(provider="gemini")
        agent.llm_provider.set_response_type("no_issues")
        agent.llm = agent.llm_provider.get_llm("logic")
        
        state = create_test_state(1)
        
        # Test analysis
        result_state = agent.analyze(state)
        
        # Verify response
        assert len(result_state.logic_results) == 1
        assert len(result_state.logic_errors) == 0
        
        # Check result
        result = result_state.logic_results[0]
        assert result["file"] == "test_file.py"
        assert result["has_issues"] == False
        assert "no logic issues detected" in result["analysis"].lower()
        
        print("✓ Logic analysis with no issues working correctly")
        print(f"✓ Issues detected: {result['has_issues']}")


def test_analyze_multiple_files():
    """Test logic analysis with multiple files"""
    print("\nTesting logic analysis with multiple files...")
    
    with patch('agents.logic_agent.FreeLLMProvider', MockFreeLLMProvider), \
         patch('agents.logic_agent.parse_code_blocks', side_effect=mock_parse_code_blocks):
        
        # Create agent and test state with multiple files
        agent = LogicAgent(provider="gemini")
        agent.llm_provider.set_response_type("complex_issues")
        agent.llm = agent.llm_provider.get_llm("logic")
        
        state = create_test_state(3)  # 3 files
        
        # Test analysis
        result_state = agent.analyze(state)
        
        # Verify response
        assert len(result_state.logic_results) == 3
        assert len(result_state.logic_errors) == 0
        
        # Check each result
        expected_files = ["test_file.py", "clean_file.py", "complex_file.py"]
        for i, result in enumerate(result_state.logic_results):
            assert result["file"] == expected_files[i]
            assert "analysis" in result
            assert "suggestions" in result
            assert "has_issues" in result
        
        print("✓ Multiple file analysis working correctly")
        print(f"✓ Files analyzed: {len(result_state.logic_results)}")


def test_analyze_error_handling():
    """Test error handling in logic analysis"""
    print("\nTesting error handling in logic analysis...")
    
    with patch('agents.logic_agent.FreeLLMProvider', MockFreeLLMProvider), \
         patch('agents.logic_agent.parse_code_blocks', side_effect=mock_parse_code_blocks):
        
        # Create agent and test state
        agent = LogicAgent(provider="gemini")
        agent.llm_provider.set_response_type("exception")
        agent.llm = agent.llm_provider.get_llm("logic")
        
        state = create_test_state(1)
        
        # Test analysis with error
        result_state = agent.analyze(state)
        
        # Verify error handling
        assert len(result_state.logic_errors) > 0
        assert "Error analyzing test_file.py" in result_state.logic_errors[0]
        assert "LLM connection failed" in result_state.logic_errors[0]
        assert result_state.logic_results == []
        
        print("✓ Error handling works correctly")
        print(f"✓ Error message: {result_state.logic_errors[0]}")


def test_analyze_empty_code_snippet():
    """Test analysis with empty code snippet"""
    print("\nTesting analysis with empty code snippet...")
    
    with patch('agents.logic_agent.FreeLLMProvider', MockFreeLLMProvider), \
         patch('agents.logic_agent.parse_code_blocks', side_effect=mock_parse_code_blocks):
        
        # Create agent
        agent = LogicAgent(provider="gemini")
        agent.llm_provider.set_response_type("issues_found")
        agent.llm = agent.llm_provider.get_llm("logic")
        
        # Create state with empty snippet
        empty_snippet = CodeSnippet(
            file_path="empty_file.py",
            content="",  # Empty content
            language="python"
        )
        
        context = AnalysisContext(
            repo_name="test-logic-repo",
            pr_id="PR-456",
            author="john.doe",
            commit_history=[],
            previous_issues=[],
            code_snippets=[empty_snippet]
        )
        state = MockWorkflowState(context)
        
        # Test analysis
        result_state = agent.analyze(state)
        
        # Verify error handling for empty snippet
        assert len(result_state.logic_errors) > 0
        assert "Error analyzing empty_file.py" in result_state.logic_errors[0]
        assert "Empty code snippet" in result_state.logic_errors[0]
        
        print("✓ Empty code snippet handling works correctly")


def test_analyze_none_snippet():
    """Test analysis with None or malformed snippet"""
    print("\nTesting analysis with None snippet...")
    
    with patch('agents.logic_agent.FreeLLMProvider', MockFreeLLMProvider):
        # Create agent
        agent = LogicAgent(provider="gemini")
        agent.llm_provider.set_response_type("issues_found")
        agent.llm = agent.llm_provider.get_llm("logic")
        
        # Create context with valid snippets first
        context = AnalysisContext(
            repo_name="test-logic-repo",
            pr_id="PR-456",
            author="john.doe",
            commit_history=[],
            previous_issues=[],
            code_snippets=[]  # Start with empty list
        )
        
        # Manually add None to the code_snippets to bypass pydantic validation
        context.code_snippets = [None]
        state = MockWorkflowState(context)
        
        # Test analysis
        result_state = agent.analyze(state)
        
        # Verify error handling
        assert len(result_state.logic_errors) > 0
        assert "Error analyzing unknown" in result_state.logic_errors[0]
        
        print("✓ None snippet handling works correctly")


def test_create_chain_functionality():
    """Test the _create_chain method functionality"""
    print("\nTesting _create_chain functionality...")
    
    with patch('agents.logic_agent.FreeLLMProvider') as mock_provider, \
         patch('agents.logic_agent.parse_code_blocks', side_effect=mock_parse_code_blocks):
        
        # Create a mock provider instance
        mock_llm = MockLLM("issues_found")
        mock_provider_instance = Mock()
        mock_provider_instance.get_llm.return_value = mock_llm
        mock_provider.return_value = mock_provider_instance
        
        # Create agent
        agent = LogicAgent(provider="gemini")
        
        # Test chain creation
        chain = agent._create_chain()
        
        # Verify chain is created
        assert chain is not None
        
        # Test chain invocation
        test_input = {
            "file_path": "test.py",
            "code": "def test(): pass"
        }
        
        result = chain.invoke(test_input)
        
        # Verify result
        assert isinstance(result, str)
        assert "Logic Analysis" in result
        
        print("✓ Chain creation and invocation works correctly")


def test_different_providers():
    """Test logic agent with different providers"""
    print("\nTesting different providers...")
    
    providers = ["gemini", "openai", "claude"]
    
    for provider in providers:
        with patch('agents.logic_agent.FreeLLMProvider') as mock_provider, \
             patch('agents.logic_agent.parse_code_blocks', side_effect=mock_parse_code_blocks):
            
            mock_llm = MockLLM("issues_found")
            mock_provider_instance = Mock()
            mock_provider_instance.get_llm.return_value = mock_llm
            mock_provider.return_value = mock_provider_instance
            
            # Create agent with different provider
            agent = LogicAgent(provider=provider)
            state = create_test_state(1)
            
            # Test analysis
            result_state = agent.analyze(state)
            
            # Verify response
            assert len(result_state.logic_results) == 1
            
            # Verify correct provider was used
            mock_provider.assert_called_with(provider)
            mock_provider_instance.get_llm.assert_called_with("logic")
    
    print("✓ Different providers work correctly")


def test_parse_code_blocks_integration():
    """Test parse_code_blocks integration"""
    print("\nTesting parse_code_blocks integration...")
    
    with patch('agents.logic_agent.FreeLLMProvider') as mock_provider, \
         patch('agents.logic_agent.parse_code_blocks', side_effect=mock_parse_code_blocks):
        
        mock_llm = MockLLM("complex_issues")
        mock_provider_instance = Mock()
        mock_provider_instance.get_llm.return_value = mock_llm
        mock_provider.return_value = mock_provider_instance
        
        # Create agent and test state
        agent = LogicAgent(provider="gemini")
        state = create_test_state(1)
        
        # Test analysis
        result_state = agent.analyze(state)
        
        # Verify suggestions were parsed
        assert len(result_state.logic_results) == 1
        result = result_state.logic_results[0]
        assert isinstance(result["suggestions"], list)
        
        print("✓ parse_code_blocks integration works correctly")


def run_performance_test():
    """Run performance test for logic analysis"""
    print("\nRunning performance test...")
    
    with patch('agents.logic_agent.FreeLLMProvider') as mock_provider, \
         patch('agents.logic_agent.parse_code_blocks', side_effect=mock_parse_code_blocks):
        
        mock_llm = MockLLM("issues_found")
        mock_provider_instance = Mock()
        mock_provider_instance.get_llm.return_value = mock_llm
        mock_provider.return_value = mock_provider_instance
        
        # Create agent
        agent = LogicAgent(provider="gemini")
        
        # Run multiple analyses
        times = []
        file_counts = [1, 2, 3]
        
        for i in range(15):  # 5 of each file count
            file_count = file_counts[i % 3]
            state = create_test_state(file_count)
            
            start_time = time.time()
            result_state = agent.analyze(state)
            duration = time.time() - start_time
            times.append(duration)
            
            assert len(result_state.logic_results) == file_count
        
        avg_time = sum(times) / len(times)
        print(f"✓ Performance test completed")
        print(f"✓ Average analysis time: {avg_time:.3f} seconds")
        print(f"✓ Min time: {min(times):.3f}s, Max time: {max(times):.3f}s")


def test_state_validation():
    """Test analysis with various state configurations"""
    print("\nTesting state validation...")
    
    with patch('agents.logic_agent.FreeLLMProvider') as mock_provider, \
         patch('agents.logic_agent.parse_code_blocks', side_effect=mock_parse_code_blocks):
        
        mock_llm = MockLLM("issues_found")
        mock_provider_instance = Mock()
        mock_provider_instance.get_llm.return_value = mock_llm
        mock_provider.return_value = mock_provider_instance
        
        agent = LogicAgent(provider="gemini")
        
        # Test with empty code_snippets list
        context = AnalysisContext(
            repo_name="test-logic-repo",
            pr_id="PR-456",
            author="john.doe",
            commit_history=[],
            previous_issues=[],
            code_snippets=[]
        )
        empty_snippets_state = MockWorkflowState(context)
        result_state = agent.analyze(empty_snippets_state)
        assert len(result_state.logic_results) == 0
        assert len(result_state.logic_errors) == 0
        
        print("✓ State validation works correctly")


def test_complex_analysis_scenarios():
    """Test complex analysis scenarios"""
    print("\nTesting complex analysis scenarios...")
    
    with patch('agents.logic_agent.FreeLLMProvider') as mock_provider, \
         patch('agents.logic_agent.parse_code_blocks', side_effect=mock_parse_code_blocks):
        
        # Test different response types
        response_types = ["issues_found", "no_issues", "complex_issues"]
        
        for response_type in response_types:
            mock_llm = MockLLM(response_type)
            mock_provider_instance = Mock()
            mock_provider_instance.get_llm.return_value = mock_llm
            mock_provider.return_value = mock_provider_instance
            
            agent = LogicAgent(provider="gemini")
            state = create_test_state(1)
            
            result_state = agent.analyze(state)
            
            assert len(result_state.logic_results) == 1
            
            result = result_state.logic_results[0]
            if response_type == "no_issues":
                assert result["has_issues"] == False
            else:
                assert result["has_issues"] == True
        
        print("✓ Complex analysis scenarios work correctly")


def main():
    """Run all Logic Agent tests"""
    print("=" * 60)
    print("LOGIC AGENT INDIVIDUAL TESTING")
    print("=" * 60)
    
    try:
        # Run all tests
        test_logic_agent_initialization()
        test_logic_agent_initialization_with_custom_llm()
        test_analyze_with_issues_found()
        test_analyze_with_no_issues()
        test_analyze_multiple_files()
        test_analyze_error_handling()
        test_analyze_empty_code_snippet()
        test_analyze_none_snippet()
        test_create_chain_functionality()
        test_different_providers()
        test_parse_code_blocks_integration()
        test_state_validation()
        test_complex_analysis_scenarios()
        run_performance_test()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED SUCCESSFULLY!")
        print("=" * 60)
        
        # Summary
        print("\nTEST SUMMARY:")
        print("✓ Initialization test - PASSED")
        print("✓ Custom LLM initialization test - PASSED")
        print("✓ Analysis with issues found test - PASSED")
        print("✓ Analysis with no issues test - PASSED")
        print("✓ Multiple files analysis test - PASSED")
        print("✓ Error handling test - PASSED")
        print("✓ Empty code snippet test - PASSED")
        print("✓ None snippet test - PASSED")
        print("✓ Chain functionality test - PASSED")
        print("✓ Different providers test - PASSED")
        print("✓ Parse code blocks integration test - PASSED")
        print("✓ State validation test - PASSED")
        print("✓ Complex analysis scenarios test - PASSED")
        print("✓ Performance test - PASSED")
        
    except Exception as e:
        print(f"\n TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()