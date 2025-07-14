import os
import sys
import json
from unittest.mock import patch, Mock, MagicMock

# Add root path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from agents.quality_agent import QualityAgent, QualityIssue
from agents.models import AgentResponse, CodeSnippet


def get_mock_snippet(file_path="test.py", content="def main(): pass"):
    return CodeSnippet(
        file_path=file_path,
        content=content,
        language="python"
    )


def test_initialization():
    print("Testing QualityAgent initialization...")

    with patch("agents.quality_agent.FreeLLMProvider") as mock_provider:
        mock_llm = Mock()
        mock_instance = mock_provider.return_value
        mock_instance.get_llm.return_value = mock_llm

        agent = QualityAgent(provider="gemini")

        assert agent.llm is mock_llm
        assert agent.prompt is not None
        assert agent.parser is not None
        print("QualityAgent initialized successfully")


def test_analyze_with_issues():
    print("\nTesting analyze method with detected issues...")

    issues = [
        {
            "type": "style",
            "description": "Missing docstring",
            "line": 1,
            "file": "test.py",
            "severity": "low",
            "rule_id": "E301"
        }
    ]
    json_response = json.dumps(issues)

    with patch("agents.quality_agent.FreeLLMProvider") as mock_provider:
        # Mock LLM provider
        mock_llm = MagicMock()
        mock_provider.return_value.get_llm.return_value = mock_llm
        
        # Create a mock chain that returns our JSON response
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = json_response
        
        # Patch the chain creation
        with patch.object(QualityAgent, '_create_chain', return_value=mock_chain):
            agent = QualityAgent()
            state = {"code_snippets": [get_mock_snippet()]}
            response = agent.analyze(state)

            assert response.success is True
            assert len(response.results) == 1
            issue = response.results[0]
            assert isinstance(issue, QualityIssue)
            assert issue.type == "style"
            assert issue.description == "Missing docstring"
            assert issue.line == 1
            assert response.errors == []
            assert response.metadata["issues_found"] == 1
            print("Quality issues properly detected and parsed")


def test_analyze_no_issues():
    print("\nTesting analyze method with no issues...")

    json_response = "[]"  # Empty issues list

    with patch("agents.quality_agent.FreeLLMProvider") as mock_provider:
        mock_llm = MagicMock()
        mock_provider.return_value.get_llm.return_value = mock_llm
        
        # Create a mock chain that returns empty JSON
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = json_response
        
        # Patch the chain creation
        with patch.object(QualityAgent, '_create_chain', return_value=mock_chain):
            agent = QualityAgent()
            state = {"code_snippets": [get_mock_snippet()]}
            response = agent.analyze(state)

            assert response.success is True
            assert len(response.results) == 0
            assert response.errors == []
            assert response.metadata["issues_found"] == 0
            print("No quality issues detected as expected")


def test_analyze_fallback_parsing():
    print("\nTesting JSON parsing fallback...")

    # Simulate invalid JSON but with quality keywords
    invalid_response = "Style issue: Missing docstring in public module"

    with patch("agents.quality_agent.FreeLLMProvider") as mock_provider:
        mock_llm = MagicMock()
        mock_provider.return_value.get_llm.return_value = mock_llm
        
        # Create a mock chain that returns invalid response
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = invalid_response
        
        # Patch the chain creation
        with patch.object(QualityAgent, '_create_chain', return_value=mock_chain):
            agent = QualityAgent()
            state = {"code_snippets": [get_mock_snippet()]}
            response = agent.analyze(state)

            assert response.success is True
            assert len(response.results) == 1
            issue = response.results[0]
            assert issue.type == "Code Quality Issue"
            assert "Style issue" in issue.description
            assert issue.line == 0
            assert response.errors == []
            print("Fallback parsing for non-JSON response successful")


def test_analyze_with_exception():
    print("\nTesting exception handling...")

    with patch("agents.quality_agent.FreeLLMProvider") as mock_provider:
        mock_llm = MagicMock()
        mock_provider.return_value.get_llm.return_value = mock_llm
        
        # Create a mock chain that raises an exception
        mock_chain = MagicMock()
        mock_chain.invoke.side_effect = Exception("LLM connection failed")
        
        # Patch the chain creation
        with patch.object(QualityAgent, '_create_chain', return_value=mock_chain):
            agent = QualityAgent()
            state = {"code_snippets": [get_mock_snippet()]}
            response = agent.analyze(state)

            assert response.success is False
            assert len(response.errors) == 1
            assert "Error analyzing test.py" in response.errors[0]
            assert "LLM connection failed" in response.errors[0]
            print("Exception during analysis properly handled")


def test_code_block_parsing():
    print("\nTesting JSON extraction from code blocks...")

    # Response wrapped in markdown code block
    issues = [{"type": "style", "description": "Invalid indentation", "line": 5}]
    wrapped_response = f"```json\n{json.dumps(issues)}\n```"

    with patch("agents.quality_agent.FreeLLMProvider") as mock_provider:
        mock_llm = MagicMock()
        mock_provider.return_value.get_llm.return_value = mock_llm
        
        # Create a mock chain that returns wrapped JSON
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = wrapped_response
        
        # Patch the chain creation
        with patch.object(QualityAgent, '_create_chain', return_value=mock_chain):
            agent = QualityAgent()
            state = {"code_snippets": [get_mock_snippet()]}
            response = agent.analyze(state)

            assert response.success is True
            assert len(response.results) == 1
            issue = response.results[0]
            assert issue.type == "style"
            assert "Invalid indentation" in issue.description
            assert issue.line == 5
            print("JSON extraction from code blocks successful")


def main():
    print("=" * 60)
    print("QUALITY AGENT UNIT TESTS")
    print("=" * 60)

    test_initialization()
    test_analyze_with_issues()
    test_analyze_no_issues()
    test_analyze_fallback_parsing()
    test_analyze_with_exception()
    test_code_block_parsing()

    print("\n" + "=" * 60)
    print("ALL QUALITY AGENT TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()