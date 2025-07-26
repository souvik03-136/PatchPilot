import json
from .models import AnalysisContext, AgentResponse, WorkflowState
from .tools import get_llm, hash_content
from langchain_core.prompts import ChatPromptTemplate
from langchain.memory import VectorStoreRetrieverMemory
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings


class ContextAgent:
    def __init__(self, provider: str = "gemini"):
        self.llm = get_llm("context", provider)

        self.embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

        self.vector_store = Chroma(
            collection_name="context_memory",
            embedding_function=self.embedding,
            persist_directory="memory_store"
        )

        self.memory = VectorStoreRetrieverMemory(
            retriever=self.vector_store.as_retriever(search_kwargs={"k": 3})
        )

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a context manager. Analyze historical data:

Developer Profile:
- Name: {author}
- Previous Issues: {previous_issues}
- Commit Patterns: {commit_patterns}

Current PR Context:
- Repo: {repo_name}
- PR: {pr_id}
- Files Changed: {changed_files}

Historical Context: {history}

Adjust severity for recurring issues and identify patterns."""),
            ("human", "Enrich context for PR: {pr_id}")
        ])

    def enrich_context(self, state: WorkflowState) -> dict:
        # Your context enrichment logic here
        return {
            "repo_analysis": {
                "total_files": len(state.context.code_snippets),
                "languages": list(set(s.language for s in state.context.code_snippets))
            },
            "historical_patterns": {
                "similar_issues": len(state.context.previous_issues)
            }
        }

    def update_severity(self, context_key: str, issue_ids: list, severity_adjust: int):
        """Adjust issue severity based on developer feedback"""
        try:
            history = self.memory.load_memory_variables({"prompt": context_key})
            updated_history = []

            for record in history:
                if isinstance(record, str):
                    try:
                        record = json.loads(record)
                    except Exception:
                        continue

                for issue in record.get("issues", []):
                    if issue.get("id") in issue_ids:
                        issue["severity"] = max(1, min(4, issue.get("severity", 2) + severity_adjust))

                updated_history.append(record)

            self.memory.save_context(
                {"input": context_key},
                {"output": json.dumps(updated_history)}
            )
            self.vector_store.persist()

        except Exception as e:
            print(f"Failed to update severity for context '{context_key}': {str(e)}")

    def _analyze_commit_history(self, history: list) -> str:
        """Extract patterns from commit messages"""
        patterns = {
            "security_fixes": sum(
                1 for c in history
                if "fix" in c.get("message", "").lower() and "security" in c.get("message", "").lower()
            ),
            "bug_fixes": sum(
                1 for c in history
                if "fix" in c.get("message", "").lower() and "bug" in c.get("message", "").lower()
            ),
            "features": sum(
                1 for c in history
                if "feat" in c.get("message", "").lower() or "feature" in c.get("message", "").lower()
            ),
        }
        return "\n".join([f"{k}: {v} occurrences" for k, v in patterns.items()])