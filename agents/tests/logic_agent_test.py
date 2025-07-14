import os
import sys
from unittest.mock import patch, Mock

# Add root path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from agents.logic_agent import LogicAgent
from agents.models import CodeSnippet, AgentResponse


def get_mock_snippet(file_path="test.py", content="def main(): pass"):
    return CodeSnippet(
        file_path=file_path,
        content=content,
        language="python"
    )


# Create a mock class that properly simulates the LangChain expression language
class ChainMock:
    def __init__(self, return_value=None):
        self.return_value = return_value
        
    def __or__(self, other):
        # Simulate chaining by returning a new ChainMock
        return ChainMock(self.return_value)
        
    def invoke(self, input_data):
        # Return the pre-configured analysis text
        return self.return_value


def test_initialization():
    print("Testing LogicAgent initialization...")

    with patch("agents.logic_agent.FreeLLMProvider") as mock_provider:
        mock_llm = Mock()
        mock_instance = mock_provider.return_value
        mock_instance.get_llm.return_value = mock_llm

        agent = LogicAgent(provider="gemini")

        assert agent.llm is mock_llm
        assert agent.prompt is not None
        print("LogicAgent initialized successfully")


def test_analyze_with_issues():
    print("\nTesting analyze method with detected issues...")

    analysis_text = """
    ## Logic Analysis for test.py

    ### Issues Found:
    1. **Infinite Loop**: Loop without break condition
       - Line: 10
       - Severity: High
       - Fix: Add a termination condition

    ### Suggestions:
    - Review loop logic
    """

    with patch("agents.logic_agent.FreeLLMProvider") as mock_provider, \
         patch("agents.logic_agent.parse_code_blocks") as mock_parse_blocks:

        # Mock the LLM provider
        mock_llm = Mock()
        mock_provider.return_value.get_llm.return_value = mock_llm
        
        # Mock parsing code blocks
        mock_parse_blocks.return_value = ["Review loop logic"]

        # Create a mock chain that returns our analysis text
        mock_chain = ChainMock(return_value=analysis_text)
        
        # Patch the chain creation to return our mock chain
        with patch.object(LogicAgent, '_create_chain', return_value=mock_chain):
            agent = LogicAgent()
            state = {
                "code_snippets": [get_mock_snippet()]
            }

            response = agent.analyze(state)

            assert isinstance(response, AgentResponse)
            assert response.success is True
            assert len(response.results) == 1
            assert response.results[0]["has_issues"] is True
            assert "analysis" in response.results[0]
            assert response.errors == []

            print("Logic analysis completed with issues detected")


def test_analyze_no_issues():
    print("\nTesting analyze method with no issues...")

    analysis_text = "No logic issues detected."

    with patch("agents.logic_agent.FreeLLMProvider") as mock_provider, \
         patch("agents.logic_agent.parse_code_blocks") as mock_parse_blocks:

        # Mock the LLM provider
        mock_llm = Mock()
        mock_provider.return_value.get_llm.return_value = mock_llm
        
        # Mock parsing code blocks
        mock_parse_blocks.return_value = []

        # Create a mock chain that returns our analysis text
        mock_chain = ChainMock(return_value=analysis_text)
        
        # Patch the chain creation to return our mock chain
        with patch.object(LogicAgent, '_create_chain', return_value=mock_chain):
            agent = LogicAgent()
            state = {
                "code_snippets": [get_mock_snippet()]
            }

            response = agent.analyze(state)

            assert isinstance(response, AgentResponse)
            assert response.success is True
            assert response.results[0]["has_issues"] is False
            assert response.errors == []
            assert response.metadata["total_files"] == 1

            print("Logic analysis completed with no issues detected")


def test_analyze_with_exception():
    print("\nTesting analyze method with exception...")

    # Create a mock chain that raises an exception when invoked
    class FailingChainMock:
        def __or__(self, other):
            return self
            
        def invoke(self, input_data):
            raise Exception("LLM failed")

    with patch("agents.logic_agent.FreeLLMProvider") as mock_provider, \
         patch.object(LogicAgent, '_create_chain') as mock_create_chain:

        # Let the agent initialize properly
        mock_llm = Mock()
        mock_provider.return_value.get_llm.return_value = mock_llm
        
        # Set up the chain to fail during analysis
        mock_create_chain.return_value = FailingChainMock()

        agent = LogicAgent()
        state = {
            "code_snippets": [get_mock_snippet()]
        }
        response = agent.analyze(state)

        assert response.success is False
        assert len(response.errors) == 1
        assert "Error analyzing" in response.errors[0]
        assert "LLM failed" in response.errors[0]

        print("Exception properly handled during analysis")


def main():
    print("=" * 60)
    print("LOGIC AGENT UNIT TESTS")
    print("=" * 60)

    try:
        test_initialization()
        test_analyze_with_issues()
        test_analyze_no_issues()
        test_analyze_with_exception()

        print("\n" + "=" * 60)
        print("ALL LOGIC AGENT TESTS PASSED")
        print("=" * 60)
    except Exception as e:
        print("\nTEST FAILED:", str(e))
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()