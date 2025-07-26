import os
import sys
import time
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from dotenv import load_dotenv

# Add root to path so `agents` can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from agents.models import AnalysisContext, CodeSnippet, Vulnerability, AgentResponse, WorkflowState
from agents.context_agent import ContextAgent

load_dotenv()


class MockLLM:
    """Mock LLM for testing"""
    def invoke(self, prompt):
        return """
        Context Analysis Results:
        - Developer Profile: test-user shows moderate risk patterns
        - Historical Issues: 2 similar security issues found in past 6 months
        - Commit Patterns: Regular committer with focus on features
        - Risk Assessment: Medium risk based on historical data
        - Recommendations: 
          * Increase scrutiny for security-related changes
          * Previous password hardcoding incidents detected
          * Consider additional security review
        """


class MockEmbeddings:
    """Mock embeddings for testing"""
    def embed_documents(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]
    
    def embed_query(self, text):
        return [0.1, 0.2, 0.3]


class MockChroma:
    """Mock Chroma vector store for testing"""
    def __init__(self, **kwargs):
        self.data = {}
        self.collection_name = kwargs.get('collection_name', 'test')
    
    def add_texts(self, texts, metadatas=None):
        for i, text in enumerate(texts):
            self.data[f"doc_{i}"] = {
                'text': text,
                'metadata': metadatas[i] if metadatas else {}
            }
    
    def similarity_search(self, query, k=3):
        # Return mock similar documents
        return [
            Mock(page_content="Previous security issue: hardcoded password in config.py"),
            Mock(page_content="Developer history: 3 security fixes in last quarter"),
            Mock(page_content="Repo pattern: Common issue with authentication logic")
        ]
    
    def as_retriever(self, **kwargs):
        retriever = Mock()
        retriever.get_relevant_documents = lambda x: self.similarity_search(x, k=kwargs.get('search_kwargs', {}).get('k', 3))
        return retriever
    
    def persist(self):
        pass


class MockVectorStoreRetrieverMemory:
    """Mock memory for testing"""
    def __init__(self, retriever):
        self.retriever = retriever
        self.memory_data = {}
    
    def load_memory_variables(self, inputs):
        key = inputs.get('prompt', 'default')
        return self.memory_data.get(key, {
            'history': [
                "Previous analysis: Developer had 2 security issues in past 6 months",
                "Pattern detected: Tendency to hardcode credentials",
                "Risk level: Medium based on historical data"
            ]
        })
    
    def save_context(self, inputs, outputs):
        key = inputs.get('input', 'default')
        self.memory_data[key] = outputs


def create_test_context():
    """Create a test AnalysisContext"""
    return AnalysisContext(
        repo_name="test-security-repo",
        pr_id="PR-456",
        author="john.doe",
        commit_history=[
            {"id": "abc123", "message": "feat: add user authentication"},
            {"id": "def456", "message": "fix: security vulnerability in login"},
            {"id": "ghi789", "message": "fix: bug in password validation"},
            {"id": "jkl012", "message": "feature: implement OAuth integration"}
        ],
        previous_issues=[
            Vulnerability(
                type="Hardcoded Credentials",
                severity="high",
                description="Password hardcoded in configuration",
                line=42,
                file="config.py",
                confidence=0.95
            ),
            Vulnerability(
                type="SQL Injection",
                severity="critical",
                description="Unsafe SQL query construction",
                line=28,
                file="database.py",
                confidence=0.88
            )
        ],
        code_snippets=[
            CodeSnippet(
                file_path="auth/login.py",
                content="""def authenticate(username, password):
    admin_pass = 'hardcoded_secret'
    if password == admin_pass:
        return True
    return validate_password(password)""",
                language="python"
            ),
            CodeSnippet(
                file_path="utils/database.py",
                content="""def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return execute_query(query)""",
                language="python"
            ),
            CodeSnippet(
                file_path="config/settings.py",
                content="""DATABASE_URL = 'sqlite:///app.db'
SECRET_KEY = 'development_key_123'
DEBUG = True""",
                language="python"
            )
        ]
    )


def create_test_workflow_state():
    """Create a test WorkflowState with AnalysisContext"""
    context = create_test_context()
    return WorkflowState(
        context=context,
        vulnerabilities=[],
        current_step="context_enrichment",
        metadata={}
    )


def test_context_agent_initialization():
    """Test ContextAgent initialization"""
    print("Testing ContextAgent initialization...")
    
    with patch('agents.context_agent.get_llm') as mock_get_llm, \
         patch('agents.context_agent.HuggingFaceEmbeddings') as mock_embeddings, \
         patch('agents.context_agent.Chroma') as mock_chroma, \
         patch('agents.context_agent.VectorStoreRetrieverMemory') as mock_memory:
        
        # Setup mocks
        mock_get_llm.return_value = MockLLM()
        mock_embeddings.return_value = MockEmbeddings()
        mock_chroma.return_value = MockChroma()
        mock_memory.return_value = MockVectorStoreRetrieverMemory(Mock())
        
        # Create agent
        agent = ContextAgent(provider="gemini")
        
        # Verify initialization
        assert agent.llm is not None
        assert agent.embedding is not None
        assert agent.vector_store is not None
        assert agent.memory is not None
        assert agent.prompt is not None
        
        print("✓ ContextAgent initialized successfully")


def test_enrich_context_success():
    """Test successful context enrichment"""
    print("\nTesting successful context enrichment...")
    
    with patch('agents.context_agent.get_llm') as mock_get_llm, \
         patch('agents.context_agent.HuggingFaceEmbeddings') as mock_embeddings, \
         patch('agents.context_agent.Chroma') as mock_chroma, \
         patch('agents.context_agent.VectorStoreRetrieverMemory') as mock_memory:
        
        # Setup mocks
        mock_llm = MockLLM()
        mock_get_llm.return_value = mock_llm
        mock_embeddings.return_value = MockEmbeddings()
        mock_vector_store = MockChroma()
        mock_chroma.return_value = mock_vector_store
        mock_memory_instance = MockVectorStoreRetrieverMemory(mock_vector_store.as_retriever())
        mock_memory.return_value = mock_memory_instance
        
        # Create agent and test workflow state
        agent = ContextAgent(provider="gemini")
        workflow_state = create_test_workflow_state()
        
        # Test enrichment
        start_time = time.time()
        response = agent.enrich_context(workflow_state)
        duration = time.time() - start_time
        
        # Verify response
        assert isinstance(response, dict)
        assert 'repo_analysis' in response
        assert 'historical_patterns' in response
        assert response['repo_analysis']['total_files'] == 3
        assert len(response['repo_analysis']['languages']) > 0
        
        print(f"✓ Context enrichment completed in {duration:.3f} seconds")
        print(f"✓ Response contains repo_analysis: {'repo_analysis' in response}")
        print(f"✓ Total files: {response['repo_analysis']['total_files']}")
        print(f"✓ Languages: {response['repo_analysis']['languages']}")


def test_enrich_context_error_handling():
    """Test error handling in context enrichment"""
    print("\nTesting error handling in context enrichment...")
    
    with patch('agents.context_agent.get_llm') as mock_get_llm, \
         patch('agents.context_agent.HuggingFaceEmbeddings') as mock_embeddings, \
         patch('agents.context_agent.Chroma') as mock_chroma, \
         patch('agents.context_agent.VectorStoreRetrieverMemory') as mock_memory:
        
        # Setup mocks to raise exception
        mock_llm = Mock()
        mock_llm.invoke.side_effect = Exception("LLM connection failed")
        mock_get_llm.return_value = mock_llm
        mock_embeddings.return_value = MockEmbeddings()
        mock_chroma.return_value = MockChroma()
        mock_memory.return_value = MockVectorStoreRetrieverMemory(Mock())
        
        # Create agent and test workflow state
        agent = ContextAgent(provider="gemini")
        workflow_state = create_test_workflow_state()
        
        # Test enrichment - should still work since it doesn't use LLM in current implementation
        response = agent.enrich_context(workflow_state)
        
        # Verify response is still valid
        assert isinstance(response, dict)
        assert 'repo_analysis' in response
        
        print("✓ Error handling works correctly")
        print(f"✓ Response type: {type(response)}")
        print(f"✓ Contains repo_analysis: {'repo_analysis' in response}")


def test_commit_history_analysis():
    """Test commit history pattern analysis"""
    print("\nTesting commit history analysis...")
    
    with patch('agents.context_agent.get_llm') as mock_get_llm, \
         patch('agents.context_agent.HuggingFaceEmbeddings') as mock_embeddings, \
         patch('agents.context_agent.Chroma') as mock_chroma, \
         patch('agents.context_agent.VectorStoreRetrieverMemory') as mock_memory:
        
        # Setup mocks
        mock_get_llm.return_value = MockLLM()
        mock_embeddings.return_value = MockEmbeddings()
        mock_chroma.return_value = MockChroma()
        mock_memory.return_value = MockVectorStoreRetrieverMemory(Mock())
        
        # Create agent
        agent = ContextAgent(provider="gemini")
        
        # Test commit history analysis
        test_history = [
            {"message": "fix: security vulnerability in authentication"},
            {"message": "feat: add new user dashboard"},
            {"message": "fix: bug in password validation"},
            {"message": "feature: implement OAuth integration"},
            {"message": "fix: security issue with session management"}
        ]
        
        patterns = agent._analyze_commit_history(test_history)
        
        # Verify patterns
        assert "security_fixes: 2 occurrences" in patterns
        assert "bug_fixes: 1 occurrences" in patterns
        assert "features: 2 occurrences" in patterns
        
        print("✓ Commit history analysis working correctly")
        print(f"✓ Patterns detected:\n{patterns}")


def test_severity_update():
    """Test severity update functionality"""
    print("\nTesting severity update functionality...")
    
    with patch('agents.context_agent.get_llm') as mock_get_llm, \
         patch('agents.context_agent.HuggingFaceEmbeddings') as mock_embeddings, \
         patch('agents.context_agent.Chroma') as mock_chroma, \
         patch('agents.context_agent.VectorStoreRetrieverMemory') as mock_memory:
        
        # Setup mocks
        mock_get_llm.return_value = MockLLM()
        mock_embeddings.return_value = MockEmbeddings()
        mock_chroma.return_value = MockChroma()
        mock_memory_instance = MockVectorStoreRetrieverMemory(Mock())
        mock_memory.return_value = mock_memory_instance
        
        # Create agent
        agent = ContextAgent(provider="gemini")
        
        # Test severity update
        context_key = "test_repo:user_hash"
        issue_ids = ["issue_1", "issue_2"]
        severity_adjust = 1
        
        # This should not raise an exception
        agent.update_severity(context_key, issue_ids, severity_adjust)
        
        print("✓ Severity update completed without errors")


def test_memory_persistence():
    """Test memory save and load functionality"""
    print("\nTesting memory persistence...")
    
    with patch('agents.context_agent.get_llm') as mock_get_llm, \
         patch('agents.context_agent.HuggingFaceEmbeddings') as mock_embeddings, \
         patch('agents.context_agent.Chroma') as mock_chroma, \
         patch('agents.context_agent.VectorStoreRetrieverMemory') as mock_memory:
        
        # Setup mocks
        mock_get_llm.return_value = MockLLM()
        mock_embeddings.return_value = MockEmbeddings()
        mock_chroma.return_value = MockChroma()
        mock_memory_instance = MockVectorStoreRetrieverMemory(Mock())
        mock_memory.return_value = mock_memory_instance
        
        # Create agent and test context
        agent = ContextAgent(provider="gemini")
        context = create_test_context()
        
        # Test memory operations
        memory_key = f"{context.repo_name}:test_hash"
        
        # Load memory (should return default)
        initial_memory = agent.memory.load_memory_variables({"prompt": memory_key})
        assert 'history' in initial_memory
        
        # Save some context
        agent.memory.save_context(
            {"input": memory_key},
            {"output": "Test context saved"}
        )
        
        print("✓ Memory persistence operations completed")


def run_performance_test():
    """Run performance test for context enrichment"""
    print("\nRunning performance test...")
    
    with patch('agents.context_agent.get_llm') as mock_get_llm, \
         patch('agents.context_agent.HuggingFaceEmbeddings') as mock_embeddings, \
         patch('agents.context_agent.Chroma') as mock_chroma, \
         patch('agents.context_agent.VectorStoreRetrieverMemory') as mock_memory:
        
        # Setup mocks
        mock_get_llm.return_value = MockLLM()
        mock_embeddings.return_value = MockEmbeddings()
        mock_chroma.return_value = MockChroma()
        mock_memory.return_value = MockVectorStoreRetrieverMemory(Mock())
        
        # Create agent
        agent = ContextAgent(provider="gemini")
        
        # Run multiple enrichments
        times = []
        for i in range(5):
            workflow_state = create_test_workflow_state()
            workflow_state.context.pr_id = f"PR-{i+1}"
            
            start_time = time.time()
            response = agent.enrich_context(workflow_state)
            duration = time.time() - start_time
            times.append(duration)
            
            assert isinstance(response, dict)
            assert 'repo_analysis' in response
        
        avg_time = sum(times) / len(times)
        print(f"✓ Performance test completed")
        print(f"✓ Average enrichment time: {avg_time:.3f} seconds")
        print(f"✓ Min time: {min(times):.3f}s, Max time: {max(times):.3f}s")


def main():
    """Run all Context Agent tests"""
    print("=" * 60)
    print("CONTEXT AGENT INDIVIDUAL TESTING")
    print("=" * 60)
    
    try:
        # Run all tests
        test_context_agent_initialization()
        test_enrich_context_success()
        test_enrich_context_error_handling()
        test_commit_history_analysis()
        test_severity_update()
        test_memory_persistence()
        run_performance_test()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED SUCCESSFULLY!")
        print("=" * 60)
        
        # Summary
        print("\nTEST SUMMARY:")
        print("✓ Initialization test - PASSED")
        print("✓ Context enrichment test - PASSED")
        print("✓ Error handling test - PASSED")
        print("✓ Commit history analysis test - PASSED")
        print("✓ Severity update test - PASSED")
        print("✓ Memory persistence test - PASSED")
        print("✓ Performance test - PASSED")
        
    except Exception as e:
        print(f"\n TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()