import os
import sys
import json
from unittest.mock import patch, Mock, MagicMock

# Add root path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from agents.security_agent import SecurityAgent, Vulnerability
from agents.models import AgentResponse, CodeSnippet


def get_mock_snippet(file_path="test.py", content="def main(): pass"):
    return CodeSnippet(
        file_path=file_path,
        content=content,
        language="python"
    )


def test_initialization():
    print("Testing SecurityAgent initialization...")

    with patch("agents.security_agent.FreeLLMProvider") as mock_provider:
        mock_llm = Mock()
        mock_instance = mock_provider.return_value
        mock_instance.get_llm.return_value = mock_llm

        agent = SecurityAgent(provider="gemini")

        assert agent.llm is mock_llm
        assert agent.prompt is not None
        assert agent.parser is not None
        print("SecurityAgent initialized successfully")


def test_analyze_with_vulnerabilities():
    print("\nTesting analyze method with vulnerabilities detected...")

    vulnerabilities = [
        {
            "type": "sql_injection",
            "severity": "high",
            "description": "Potential SQL injection vulnerability",
            "line": 42,
            "file": "test.py",
            "confidence": 0.9
        }
    ]
    json_response = json.dumps(vulnerabilities)

    with patch("agents.security_agent.FreeLLMProvider") as mock_provider:
        # Mock LLM provider
        mock_llm = MagicMock()
        mock_provider.return_value.get_llm.return_value = mock_llm
        
        # Create a mock chain that returns our JSON response
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = json_response
        
        # Patch the chain creation
        with patch.object(SecurityAgent, '_create_chain', return_value=mock_chain):
            agent = SecurityAgent()
            state = {"code_snippets": [get_mock_snippet()]}
            response = agent.analyze(state)

            assert response.success is True
            assert len(response.results) == 1
            vuln = response.results[0]
            assert isinstance(vuln, Vulnerability)
            assert vuln.type == "sql_injection"
            assert "SQL injection" in vuln.description
            assert vuln.line == 42
            assert vuln.severity == "high"
            assert vuln.confidence == 0.9
            assert response.errors == []
            assert response.metadata["issues_found"] == 1
            print("Security vulnerabilities properly detected and parsed")


def test_analyze_no_vulnerabilities():
    print("\nTesting analyze method with no vulnerabilities...")

    json_response = "[]"  # Empty vulnerabilities list

    with patch("agents.security_agent.FreeLLMProvider") as mock_provider:
        mock_llm = MagicMock()
        mock_provider.return_value.get_llm.return_value = mock_llm
        
        # Create a mock chain that returns empty JSON
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = json_response
        
        # Patch the chain creation
        with patch.object(SecurityAgent, '_create_chain', return_value=mock_chain):
            agent = SecurityAgent()
            state = {"code_snippets": [get_mock_snippet()]}
            response = agent.analyze(state)

            assert response.success is True
            assert len(response.results) == 0
            assert response.errors == []
            assert response.metadata["issues_found"] == 0
            print("No security vulnerabilities detected as expected")


def test_analyze_fallback_parsing():
    print("\nTesting JSON parsing fallback...")

    # Simulate invalid JSON but with security keywords
    invalid_response = "Security vulnerability: Hardcoded API key detected"

    with patch("agents.security_agent.FreeLLMProvider") as mock_provider:
        mock_llm = MagicMock()
        mock_provider.return_value.get_llm.return_value = mock_llm
        
        # Create a mock chain that returns invalid response
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = invalid_response
        
        # Patch the chain creation
        with patch.object(SecurityAgent, '_create_chain', return_value=mock_chain):
            agent = SecurityAgent()
            state = {"code_snippets": [get_mock_snippet()]}
            response = agent.analyze(state)

            assert response.success is True
            assert len(response.results) == 1
            vuln = response.results[0]
            assert vuln.type == "Potential Security Issue"
            assert "Hardcoded API key" in vuln.description
            assert vuln.line == 0
            assert vuln.severity == "medium"
            assert vuln.confidence == 0.6
            assert response.errors == []
            print("Fallback parsing for non-JSON response successful")


def test_analyze_with_exception():
    print("\nTesting exception handling...")

    with patch("agents.security_agent.FreeLLMProvider") as mock_provider:
        mock_llm = MagicMock()
        mock_provider.return_value.get_llm.return_value = mock_llm
        
        # Create a mock chain that raises an exception
        mock_chain = MagicMock()
        mock_chain.invoke.side_effect = Exception("LLM connection failed")
        
        # Patch the chain creation
        with patch.object(SecurityAgent, '_create_chain', return_value=mock_chain):
            agent = SecurityAgent()
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
    vulnerabilities = [{
        "type": "xss",
        "severity": "critical",
        "description": "XSS vulnerability in user input",
        "line": 15,
        "confidence": 0.95
    }]
    wrapped_response = f"```json\n{json.dumps(vulnerabilities)}\n```"

    with patch("agents.security_agent.FreeLLMProvider") as mock_provider:
        mock_llm = MagicMock()
        mock_provider.return_value.get_llm.return_value = mock_llm
        
        # Create a mock chain that returns wrapped JSON
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = wrapped_response
        
        # Patch the chain creation
        with patch.object(SecurityAgent, '_create_chain', return_value=mock_chain):
            agent = SecurityAgent()
            state = {"code_snippets": [get_mock_snippet()]}
            response = agent.analyze(state)

            assert response.success is True
            assert len(response.results) == 1
            vuln = response.results[0]
            assert vuln.type == "xss"
            assert "XSS vulnerability" in vuln.description
            assert vuln.line == 15
            assert vuln.severity == "critical"
            assert vuln.confidence == 0.95
            print("JSON extraction from code blocks successful")


def test_multiple_vulnerabilities():
    print("\nTesting multiple vulnerabilities in one file...")

    vulnerabilities = [
        {
            "type": "hardcoded_secret",
            "severity": "critical",
            "description": "Hardcoded API key in source code",
            "line": 10,
            "confidence": 0.99
        },
        {
            "type": "sql_injection",
            "severity": "high",
            "description": "User input directly used in SQL query",
            "line": 25,
            "confidence": 0.85
        }
    ]
    json_response = json.dumps(vulnerabilities)

    with patch("agents.security_agent.FreeLLMProvider") as mock_provider:
        mock_llm = MagicMock()
        mock_provider.return_value.get_llm.return_value = mock_llm
        
        # Create a mock chain that returns multiple vulnerabilities
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = json_response
        
        # Patch the chain creation
        with patch.object(SecurityAgent, '_create_chain', return_value=mock_chain):
            agent = SecurityAgent()
            state = {"code_snippets": [get_mock_snippet()]}
            response = agent.analyze(state)

            assert response.success is True
            assert len(response.results) == 2
            vuln1, vuln2 = response.results
            
            assert vuln1.type == "hardcoded_secret"
            assert "API key" in vuln1.description
            assert vuln1.line == 10
            assert vuln1.severity == "critical"
            
            assert vuln2.type == "sql_injection"
            assert "SQL query" in vuln2.description
            assert vuln2.line == 25
            assert vuln2.severity == "high"
            
            assert response.metadata["issues_found"] == 2
            print("Multiple vulnerabilities properly detected")


def test_multi_file_analysis():
    print("\nTesting analysis of multiple files...")

    vulnerabilities1 = [{
        "type": "xss",
        "severity": "high",
        "description": "XSS in user input",
        "line": 8
    }]
    
    vulnerabilities2 = [{
        "type": "path_traversal",
        "severity": "medium",
        "description": "Potential path traversal vulnerability",
        "line": 15
    }]
    
    # Mock different responses for different files
    def mock_invoke(input_data):
        if input_data["file_path"] == "file1.py":
            return json.dumps(vulnerabilities1)
        elif input_data["file_path"] == "file2.py":
            return json.dumps(vulnerabilities2)
        return "[]"

    with patch("agents.security_agent.FreeLLMProvider") as mock_provider:
        mock_llm = MagicMock()
        mock_provider.return_value.get_llm.return_value = mock_llm
        
        # Create a mock chain with different responses per file
        mock_chain = MagicMock()
        mock_chain.invoke.side_effect = mock_invoke
        
        # Patch the chain creation
        with patch.object(SecurityAgent, '_create_chain', return_value=mock_chain):
            agent = SecurityAgent()
            state = {
                "code_snippets": [
                    get_mock_snippet("file1.py", "print('Hello')"),
                    get_mock_snippet("file2.py", "open('file.txt')")
                ]
            }
            response = agent.analyze(state)

            assert response.success is True
            assert len(response.results) == 2
            assert response.metadata["total_files"] == 2
            assert response.metadata["issues_found"] == 2
            
            file1_issues = [v for v in response.results if v.file == "file1.py"]
            file2_issues = [v for v in response.results if v.file == "file2.py"]
            
            assert len(file1_issues) == 1
            assert file1_issues[0].type == "xss"
            
            assert len(file2_issues) == 1
            assert file2_issues[0].type == "path_traversal"
            
            print("Multi-file analysis successful")


def main():
    print("=" * 60)
    print("SECURITY AGENT UNIT TESTS")
    print("=" * 60)

    test_initialization()
    test_analyze_with_vulnerabilities()
    test_analyze_no_vulnerabilities()
    test_analyze_fallback_parsing()
    test_analyze_with_exception()
    test_code_block_parsing()
    test_multiple_vulnerabilities()
    test_multi_file_analysis()

    print("\n" + "=" * 60)
    print("ALL SECURITY AGENT TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()