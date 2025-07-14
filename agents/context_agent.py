import json
from .models import AnalysisContext, AgentResponse
from .tools import get_llm, hash_content
from langchain_core.prompts import ChatPromptTemplate
from langchain.memory import VectorStoreRetrieverMemory
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings


class ContextAgent:
    def __init__(self, provider: str = "gemini"):
        self.llm = get_llm("context", provider)

        # Load embedding model
        self.embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

        # Use Chroma as vector store (persistent local storage)
        self.vector_store = Chroma(
            collection_name="context_memory",
            embedding_function=self.embedding,
            persist_directory="memory_store"
        )

        # Set up retriever-based memory
        self.memory = VectorStoreRetrieverMemory(
            retriever=self.vector_store.as_retriever(search_kwargs={"k": 3})
        )

        # Prompt template for LLM
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

    def enrich_context(self, context: AnalysisContext) -> AgentResponse:
        try:
            # Create memory key
            memory_key = f"{context.repo_name}:{hash_content(context.author)}"

            # Retrieve past memory
            history = self.memory.load_memory_variables({"prompt": memory_key})

            # Analyze commit message patterns
            commit_patterns = self._analyze_commit_history(context.commit_history)

            # Format prompt
            prompt = self.prompt.format(
                repo_name=context.repo_name,
                pr_id=context.pr_id,
                author=context.author,
                previous_issues=str(context.previous_issues[:5]),
                changed_files=", ".join([s.file_path for s in context.code_snippets]),
                commit_patterns=commit_patterns,
                history=history,
            )

            # Run LLM
            response = self.llm.invoke(prompt)

            # Store updated context
            self.memory.save_context({"input": memory_key}, {"output": response})
            self.vector_store.persist()

            return AgentResponse(
                success=True,
                results=[response],
                metadata={"memory_key": memory_key}
            )

        except Exception as e:
            return AgentResponse(
                success=False,
                errors=[f"Context enrichment failed: {str(e)}"]
            )

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


'''
This updated ContextAgent:

Uses vector memory retrieval to learn from historical dev context.

Enriches PR analysis with past patterns and commit insights.

Stores and retrieves context to/from Chroma for scalable memory.'''