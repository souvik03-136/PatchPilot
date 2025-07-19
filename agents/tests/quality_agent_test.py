import os
import sys
import json
import tempfile
import pytest
from unittest.mock import patch, Mock, MagicMock, call
from dotenv import load_dotenv

# Add root to path so `agents` can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from agents.quality_agent import QualityAgent, QualityIssue
from agents.models import AgentResponse, CodeSnippet

load_dotenv()


class TestCodeSamples:
    """Real code samples for testing instead of hardcoded responses"""
    
    GOOD_PYTHON_CODE = '''
def calculate_fibonacci(n: int) -> int:
    """
    Calculate the nth Fibonacci number using dynamic programming.
    
    Args:
        n: The position in the Fibonacci sequence
        
    Returns:
        The nth Fibonacci number
        
    Raises:
        ValueError: If n is negative
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    
    if n <= 1:
        return n
    
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    
    return b
'''
    
    BAD_PYTHON_CODE = '''
def calc(x):
    if x<0:
        return None
    if x==0:
        return 0
    if x==1:
        return 1
    
    a=0
    b=1
    for i in range(2,x+1):
        temp=a+b
        a=b
        b=temp
    return b
'''

    COMPLEX_PYTHON_CODE = '''
import requests
import json

def get_user_data(user_id):
    # This function has several quality issues
    url = f"https://api.example.com/users/{user_id}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = json.loads(response.text)
        return data
    else:
        print("Error occurred")
        return None

class UserManager:
    def __init__(self):
        self.users = []
    
    def add_user(self, user):
        self.users.append(user)
    
    def find_user(self, user_id):
        for user in self.users:
            if user.id == user_id:
                return user
        return None
    
    def delete_user(self, user_id):
        for i, user in enumerate(self.users):
            if user.id == user_id:
                del self.users[i]
                return True
        return False
'''

    JAVASCRIPT_CODE = '''
function calculateTotal(items) {
    var total = 0;
    for (var i = 0; i < items.length; i++) {
        total += items[i].price;
    }
    return total;
}

const processOrder = (order) => {
    if (!order) return null;
    
    const total = calculateTotal(order.items);
    
    return {
        id: order.id,
        total: total,
        processed: true
    };
};
'''


def create_code_snippet(file_path: str, content: str, language: str = "python") -> CodeSnippet:
    """Create a CodeSnippet object for testing"""
    return CodeSnippet(
        file_path=file_path,
        content=content,
        language=language
    )


class TestQualityAgentInitialization:
    """Test QualityAgent initialization and configuration"""
    
    def test_initialization_with_default_provider(self):
        """Test initialization with default provider"""
        print("Testing QualityAgent initialization with default provider...")
        
        with patch("agents.quality_agent.FreeLLMProvider") as mock_provider:
            mock_llm = Mock()
            mock_instance = mock_provider.return_value
            mock_instance.get_llm.return_value = mock_llm
            
            agent = QualityAgent()
            
            assert agent.llm is mock_llm
            assert agent.prompt is not None
            assert agent.parser is not None
            mock_provider.assert_called_once()
            print("✓ Default provider initialization successful")
    
    def test_initialization_with_custom_provider(self):
        """Test initialization with custom provider"""
        print("Testing QualityAgent initialization with custom provider...")
        
        with patch("agents.quality_agent.FreeLLMProvider") as mock_provider:
            mock_llm = Mock()
            mock_instance = mock_provider.return_value
            mock_instance.get_llm.return_value = mock_llm
            
            agent = QualityAgent(provider="gemini")
            
            assert agent.llm is mock_llm
            mock_provider.assert_called_once_with("gemini")
            print("✓ Custom provider initialization successful")
    
def test_prompt_template_creation(self):
    """Test that prompt template is properly created"""
    print("Testing prompt template creation...")
    
    with patch("agents.quality_agent.FreeLLMProvider") as mock_provider:
        mock_llm = Mock()
        mock_instance = mock_provider.return_value
        mock_instance.get_llm.return_value = mock_llm
        
        agent = QualityAgent()
        
        # Get formatted prompt content - use 'code' instead of 'content'
        formatted_prompt = agent.prompt.format(
            file_path="test.py",
            code="sample code",  # Changed from 'content' to 'code'
            language="python"
        ).to_string()
        
        # Check that prompt contains expected elements
        assert "code quality" in formatted_prompt.lower()
        assert "file_path" in formatted_prompt
        assert "code" in formatted_prompt
        assert "language" in formatted_prompt
        print("✓ Prompt template created with required elements")

class TestQualityAgentAnalysis:
    """Test QualityAgent analysis functionality"""
    
    def test_analyze_good_quality_code(self):
        """Test analysis of high-quality code"""
        print("Testing analysis of good quality code...")
        
        # Mock LLM to return no issues for good code
        mock_response = json.dumps([])
        
        with patch("agents.quality_agent.FreeLLMProvider") as mock_provider:
            mock_llm = MagicMock()
            mock_provider.return_value.get_llm.return_value = mock_llm
            
            mock_chain = MagicMock()
            mock_chain.invoke.return_value = mock_response
            
            with patch.object(QualityAgent, '_create_chain', return_value=mock_chain):
                agent = QualityAgent()
                
                snippets = [create_code_snippet("good_code.py", TestCodeSamples.GOOD_PYTHON_CODE)]
                state = {"code_snippets": snippets}
                
                response = agent.analyze(state)
                
                assert response.success is True
                assert len(response.results) == 0
                assert response.errors == []
                assert response.metadata["issues_found"] == 0
                print("✓ Good quality code analysis successful - no issues found")
    
    def test_analyze_bad_quality_code(self):
        """Test analysis of poor quality code"""
        print("Testing analysis of poor quality code...")
        
        # Mock LLM to return quality issues
        mock_issues = [
            {
                "type": "style",
                "description": "Missing docstring for function",
                "line": 1,
                "file": "bad_code.py",
                "severity": "medium",
                "rule_id": "D100"
            },
            {
                "type": "formatting",
                "description": "Missing spaces around operator",
                "line": 2,
                "file": "bad_code.py",
                "severity": "low",
                "rule_id": "E225"
            },
            {
                "type": "naming",
                "description": "Function name should be more descriptive",
                "line": 1,
                "file": "bad_code.py",
                "severity": "medium",
                "rule_id": "N802"
            }
        ]
        mock_response = json.dumps(mock_issues)
        
        with patch("agents.quality_agent.FreeLLMProvider") as mock_provider:
            mock_llm = MagicMock()
            mock_provider.return_value.get_llm.return_value = mock_llm
            
            mock_chain = MagicMock()
            mock_chain.invoke.return_value = mock_response
            
            with patch.object(QualityAgent, '_create_chain', return_value=mock_chain):
                agent = QualityAgent()
                
                snippets = [create_code_snippet("bad_code.py", TestCodeSamples.BAD_PYTHON_CODE)]
                state = {"code_snippets": snippets}
                
                response = agent.analyze(state)
                
                assert response.success is True
                assert len(response.results) == 3
                assert response.errors == []
                assert response.metadata["issues_found"] == 3
                
                # Verify issue details
                issues = response.results
                assert isinstance(issues[0], QualityIssue)
                assert issues[0].type == "style"
                assert issues[0].description == "Missing docstring for function"
                assert issues[0].line == 1
                assert issues[0].file == "bad_code.py"
                assert issues[0].severity == "medium"
                
                print("✓ Poor quality code analysis successful - issues detected")
    
    def test_analyze_multiple_files(self):
        """Test analysis of multiple code files"""
        print("Testing analysis of multiple code files...")
        
        # Mock different responses for different files
        def mock_invoke(inputs):
            if "good_code.py" in str(inputs):
                return json.dumps([])
            elif "bad_code.py" in str(inputs):
                return json.dumps([{
                    "type": "style",
                    "description": "Missing docstring",
                    "line": 1,
                    "file": "bad_code.py",
                    "severity": "medium",
                    "rule_id": "D100"
                }])
            else:
                return json.dumps([])
        
        with patch("agents.quality_agent.FreeLLMProvider") as mock_provider:
            mock_llm = MagicMock()
            mock_provider.return_value.get_llm.return_value = mock_llm
            
            mock_chain = MagicMock()
            mock_chain.invoke.side_effect = mock_invoke
            
            with patch.object(QualityAgent, '_create_chain', return_value=mock_chain):
                agent = QualityAgent()
                
                snippets = [
                    create_code_snippet("good_code.py", TestCodeSamples.GOOD_PYTHON_CODE),
                    create_code_snippet("bad_code.py", TestCodeSamples.BAD_PYTHON_CODE),
                    create_code_snippet("complex_code.py", TestCodeSamples.COMPLEX_PYTHON_CODE)
                ]
                state = {"code_snippets": snippets}
                
                response = agent.analyze(state)
                
                assert response.success is True
                assert len(response.results) == 1  # Only bad_code.py has issues
                assert response.errors == []
                assert response.metadata["issues_found"] == 1
                
                print("✓ Multiple files analysis successful")
    
    def test_analyze_different_languages(self):
        """Test analysis of different programming languages"""
        print("Testing analysis of different programming languages...")
        
        mock_issues = [
            {
                "type": "style",
                "description": "Use const/let instead of var",
                "line": 2,
                "file": "script.js",
                "severity": "medium",
                "rule_id": "no-var"
            }
        ]
        mock_response = json.dumps(mock_issues)
        
        with patch("agents.quality_agent.FreeLLMProvider") as mock_provider:
            mock_llm = MagicMock()
            mock_provider.return_value.get_llm.return_value = mock_llm
            
            mock_chain = MagicMock()
            mock_chain.invoke.return_value = mock_response
            
            with patch.object(QualityAgent, '_create_chain', return_value=mock_chain):
                agent = QualityAgent()
                
                snippets = [
                    create_code_snippet("script.js", TestCodeSamples.JAVASCRIPT_CODE, "javascript")
                ]
                state = {"code_snippets": snippets}
                
                response = agent.analyze(state)
                
                assert response.success is True
                assert len(response.results) == 1
                assert response.results[0].type == "style"
                assert "var" in response.results[0].description
                
                print("✓ Different languages analysis successful")


class TestQualityAgentErrorHandling:
    """Test QualityAgent error handling"""
    
    def test_llm_connection_error(self):
        """Test handling of LLM connection errors"""
        print("Testing LLM connection error handling...")
        
        with patch("agents.quality_agent.FreeLLMProvider") as mock_provider:
            mock_llm = MagicMock()
            mock_provider.return_value.get_llm.return_value = mock_llm
            
            mock_chain = MagicMock()
            mock_chain.invoke.side_effect = Exception("LLM connection failed")
            
            with patch.object(QualityAgent, '_create_chain', return_value=mock_chain):
                agent = QualityAgent()
                
                snippets = [create_code_snippet("test.py", TestCodeSamples.GOOD_PYTHON_CODE)]
                state = {"code_snippets": snippets}
                
                response = agent.analyze(state)
                
                assert response.success is False
                assert len(response.errors) == 1
                assert "Error analyzing test.py" in response.errors[0]
                assert "LLM connection failed" in response.errors[0]
                
                print("✓ LLM connection error handled properly")
    
def test_invalid_json_response(self):
    """Test handling of invalid JSON responses"""
    print("Testing invalid JSON response handling...")
    
    # Invalid JSON but contains quality indicators
    invalid_response = """
    The code has several quality issues:
    1. Missing docstring for the function
    2. Poor variable naming (x instead of number)
    3. Inconsistent spacing around operators
    """
    
    with patch("agents.quality_agent.FreeLLMProvider") as mock_provider:
        mock_llm = MagicMock()
        mock_provider.return_value.get_llm.return_value = mock_llm
        
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = invalid_response
        
        with patch.object(QualityAgent, '_create_chain', return_value=mock_chain):
            agent = QualityAgent()
            
            snippets = [create_code_snippet("test.py", TestCodeSamples.BAD_PYTHON_CODE)]
            state = {"code_snippets": snippets}
            
            response = agent.analyze(state)
            
            # The fallback creates one issue per file
            assert response.success is True
            assert len(response.results) == 1
            issue = response.results[0]
            assert issue.type == "Code Quality Issue"
            assert "quality issues" in issue.description
            assert issue.line == 0
            assert issue.file == "test.py"
            
            print("✓ Invalid JSON response handled with fallback parsing")

# Update test_malformed_json_with_code_blocks in TestQualityAgentErrorHandling
def test_malformed_json_with_code_blocks(self):
    """Test handling of JSON wrapped in code blocks"""
    print("Testing JSON extraction from code blocks...")
    
    issues = [
        {
            "type": "complexity",
            "description": "Function is too complex",
            "line": 10,
            "file": "complex.py",
            "severity": "high",
            "rule_id": "C901"
        }
    ]
    
    # JSON wrapped in markdown code block
    wrapped_response = f"""
    Here's the analysis result:
    
    ```json
    {json.dumps(issues)}
    ```
    
    The code has complexity issues.
    """
    
    with patch("agents.quality_agent.FreeLLMProvider") as mock_provider:
        mock_llm = MagicMock()
        mock_provider.return_value.get_llm.return_value = mock_llm
        
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = wrapped_response
        
        with patch.object(QualityAgent, '_create_chain', return_value=mock_chain):
            agent = QualityAgent()
            
            snippets = [create_code_snippet("complex.py", TestCodeSamples.COMPLEX_PYTHON_CODE)]
            state = {"code_snippets": snippets}
            
            response = agent.analyze(state)
            
            assert response.success is True
            assert len(response.results) == 1
            issue = response.results[0]
            # Should be the actual type from JSON
            assert issue.type == "complexity"
            assert "too complex" in issue.description
            assert issue.line == 10
            assert issue.severity == "high"
            
            print("✓ JSON extraction from code blocks successful")
    
    def test_empty_code_snippets(self):
        """Test handling of empty code snippets"""
        print("Testing empty code snippets handling...")
        
        with patch("agents.quality_agent.FreeLLMProvider") as mock_provider:
            mock_llm = MagicMock()
            mock_provider.return_value.get_llm.return_value = mock_llm
            
            agent = QualityAgent()
            
            state = {"code_snippets": []}
            response = agent.analyze(state)
            
            assert response.success is True
            assert len(response.results) == 0
            assert response.errors == []
            assert response.metadata["issues_found"] == 0
            
            print("✓ Empty code snippets handled properly")
    
    def test_malformed_json_with_code_blocks(self):
        """Test handling of JSON wrapped in code blocks"""
        print("Testing JSON extraction from code blocks...")
        
        issues = [
            {
                "type": "complexity",
                "description": "Function is too complex",
                "line": 10,
                "file": "complex.py",
                "severity": "high",
                "rule_id": "C901"
            }
        ]
        
        # JSON wrapped in markdown code block
        wrapped_response = f"""
        Here's the analysis result:
        
        ```json
        {json.dumps(issues)}
        ```
        
        The code has complexity issues.
        """
        
        with patch("agents.quality_agent.FreeLLMProvider") as mock_provider:
            mock_llm = MagicMock()
            mock_provider.return_value.get_llm.return_value = mock_llm
            
            mock_chain = MagicMock()
            mock_chain.invoke.return_value = wrapped_response
            
            with patch.object(QualityAgent, '_create_chain', return_value=mock_chain):
                agent = QualityAgent()
                
                snippets = [create_code_snippet("complex.py", TestCodeSamples.COMPLEX_PYTHON_CODE)]
                state = {"code_snippets": snippets}
                
                response = agent.analyze(state)
                
                assert response.success is True
                assert len(response.results) == 1
                issue = response.results[0]
                assert issue.type == "complexity"
                assert "too complex" in issue.description
                assert issue.line == 10
                assert issue.severity == "high"
                
                print("✓ JSON extraction from code blocks successful")


class TestQualityIssueModel:
    """Test QualityIssue model functionality"""
    
    def test_quality_issue_creation(self):
        """Test QualityIssue object creation"""
        print("Testing QualityIssue creation...")
        
        issue = QualityIssue(
            type="style",
            description="Missing docstring",
            line=5,
            file="test.py",
            severity="medium",
            rule_id="D100"
        )
        
        assert issue.type == "style"
        assert issue.description == "Missing docstring"
        assert issue.line == 5
        assert issue.file == "test.py"
        assert issue.severity == "medium"
        assert issue.rule_id == "D100"
        
        print("✓ QualityIssue creation successful")
    
    def test_quality_issue_string_representation(self):
        """Test QualityIssue string representation"""
        print("Testing QualityIssue string representation...")
        
        issue = QualityIssue(
            type="naming",
            description="Variable name should be more descriptive",
            line=12,
            file="utils.py",
            severity="low"
        )
        
        str_repr = str(issue)
        assert "naming" in str_repr
        assert "Variable name should be more descriptive" in str_repr
        assert "utils.py" in str_repr
        assert "12" in str_repr
        
        print("✓ QualityIssue string representation working")


class TestQualityAgentIntegration:
    """Integration tests for QualityAgent"""
    
    def test_full_analysis_pipeline(self):
        """Test complete analysis pipeline"""
        print("Testing complete analysis pipeline...")
        
        # Mock comprehensive response
        comprehensive_issues = [
            {
                "type": "style",
                "description": "Missing docstring for function",
                "line": 1,
                "file": "main.py",
                "severity": "medium",
                "rule_id": "D100"
            },
            {
                "type": "complexity",
                "description": "Function has too many branches",
                "line": 15,
                "file": "main.py",
                "severity": "high",
                "rule_id": "C901"
            },
            {
                "type": "security",
                "description": "Potential security issue with direct string formatting",
                "line": 8,
                "file": "main.py",
                "severity": "high",
                "rule_id": "S001"
            }
        ]
        
        mock_response = json.dumps(comprehensive_issues)
        
        with patch("agents.quality_agent.FreeLLMProvider") as mock_provider:
            mock_llm = MagicMock()
            mock_provider.return_value.get_llm.return_value = mock_llm
            
            mock_chain = MagicMock()
            mock_chain.invoke.return_value = mock_response
            
            with patch.object(QualityAgent, '_create_chain', return_value=mock_chain):
                agent = QualityAgent()
                
                snippets = [create_code_snippet("main.py", TestCodeSamples.COMPLEX_PYTHON_CODE)]
                state = {"code_snippets": snippets}
                
                response = agent.analyze(state)
                
                assert response.success is True
                assert len(response.results) == 3
                assert response.errors == []
                assert response.metadata["issues_found"] == 3
                
                # Verify different issue types
                issue_types = [issue.type for issue in response.results]
                assert "style" in issue_types
                assert "complexity" in issue_types
                assert "security" in issue_types
                
                # Verify severity levels
                severities = [issue.severity for issue in response.results]
                assert "medium" in severities
                assert "high" in severities
                
                print("✓ Complete analysis pipeline successful")
    
    def test_performance_with_large_codebase(self):
        """Test performance with multiple large files"""
        print("Testing performance with large codebase...")
        
        # Create multiple code snippets
        large_snippets = []
        for i in range(10):
            content = TestCodeSamples.COMPLEX_PYTHON_CODE * 3  # Make it larger
            large_snippets.append(create_code_snippet(f"file_{i}.py", content))
        
        mock_response = json.dumps([])  # No issues for performance test
        
        with patch("agents.quality_agent.FreeLLMProvider") as mock_provider:
            mock_llm = MagicMock()
            mock_provider.return_value.get_llm.return_value = mock_llm
            
            mock_chain = MagicMock()
            mock_chain.invoke.return_value = mock_response
            
            with patch.object(QualityAgent, '_create_chain', return_value=mock_chain):
                agent = QualityAgent()
                
                state = {"code_snippets": large_snippets}
                
                import time
                start_time = time.time()
                response = agent.analyze(state)
                duration = time.time() - start_time
                
                assert response.success is True
                assert len(response.results) == 0
                assert response.errors == []
                
                # Should complete within reasonable time
                assert duration < 30  # 30 seconds max for 10 files
                
                print(f"✓ Performance test completed in {duration:.2f} seconds")


def run_all_tests():
    """Run all Quality Agent tests"""
    print("=" * 80)
    print("COMPREHENSIVE QUALITY AGENT TESTS")
    print("=" * 80)
    
    test_classes = [
        TestQualityAgentInitialization,
        TestQualityAgentAnalysis,
        TestQualityAgentErrorHandling,
        TestQualityIssueModel,
        TestQualityAgentIntegration
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for test_class in test_classes:
        print(f"\n{test_class.__name__}:")
        print("-" * 60)
        
        instance = test_class()
        methods = [method for method in dir(instance) if method.startswith('test_')]
        
        for method_name in methods:
            total_tests += 1
            try:
                method = getattr(instance, method_name)
                method()
                passed_tests += 1
                print(f"✓ {method_name}")
            except Exception as e:
                print(f"✗ {method_name}: {str(e)}")
                import traceback
                traceback.print_exc()
    
    print("\n" + "=" * 80)
    print(f"QUALITY AGENT TESTS SUMMARY: {passed_tests}/{total_tests} PASSED")
    print("=" * 80)
    
    if passed_tests == total_tests:
        print(" ALL TESTS PASSED SUCCESSFULLY!")
        return True
    else:
        print(f" {total_tests - passed_tests} TESTS FAILED")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)