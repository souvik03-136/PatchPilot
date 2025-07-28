import json
import os
import logging
import numpy as np
from onnxruntime import InferenceSession
from transformers import AutoTokenizer
from huggingface_hub import hf_hub_download

from .models import AnalysisContext, AgentResponse, WorkflowState
from .tools import get_llm, hash_content

from langchain_core.prompts import ChatPromptTemplate
from langchain.memory import VectorStoreRetrieverMemory
from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings

import chromadb

# Logging setup
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class ONNXEmbeddings(Embeddings):
    """Custom embedding class using ONNX runtime for CPU efficiency."""

    def __init__(self, model_repo="sentence-transformers/all-MiniLM-L6-v2"):
        self.model_repo = model_repo
        self.model_path = self._download_model()
        self.session = InferenceSession(self.model_path, providers=["CPUExecutionProvider"])

        # Load tokenizer for preprocessing
        self.tokenizer = AutoTokenizer.from_pretrained(model_repo)
        self.input_names = [inp.name for inp in self.session.get_inputs()]

    def _download_model(self) -> str:
        logger.info("Downloading ONNX embedding model if not present...")
        path = hf_hub_download(
            repo_id=self.model_repo,
            filename="onnx/model.onnx",
            local_dir="onnx_model",
            local_dir_use_symlinks=False
        )
        logger.info(f"Model downloaded to: {path}")
        return path

    def _preprocess(self, texts):
        """Tokenize input text for ONNX model."""
        return self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            return_tensors="np"
        )

    def embed_documents(self, texts):
        """Embed a list of documents."""
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text):
        """Embed a single query text."""
        inputs = self._preprocess([text])
        ort_inputs = {name: inputs[name] for name in self.input_names if name in inputs}

        outputs = self.session.run(None, ort_inputs)
        embeddings = outputs[0][0]  # (1, hidden_dim)
        return embeddings.tolist()


class ContextAgent:
    def __init__(self, provider: str = "gemini", device: str = "cpu"):
        if provider not in ["gemini", "openai", "anthropic"]:
            raise ValueError(f"Unsupported provider: {provider}")

        self.llm = get_llm("context", provider)

        try:
            # Initialize ONNX embeddings
            self.embedding = ONNXEmbeddings()

            # Create persistent directory if not exists
            persist_dir = "memory_store"
            os.makedirs(persist_dir, exist_ok=True)

            # Initialize Chroma client with new API
            client = chromadb.PersistentClient(path=persist_dir)

            # Initialize vector store
            self.vector_store = Chroma(
                client=client,
                collection_name="context_memory",
                embedding_function=self.embedding,
            )

        except Exception as e:
            raise RuntimeError(f"Failed to initialize embedding model: {str(e)}")

        # Memory retriever
        self.memory = VectorStoreRetrieverMemory(
            retriever=self.vector_store.as_retriever(search_kwargs={"k": 3})
        )

        # Prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """You are a context manager. Analyze historical data:

Developer Profile:
- Name: {author}
- Previous Issues: {previous_issues}
- Commit Patterns: {commit_patterns}

Current PR Context:
- Repo: {repo_name}
- PR: {pr_id}
- Files Changed: {changed_files}

Historical Context: {history}

Adjust severity for recurring issues and identify patterns."""
            ),
            ("human", "Enrich context for PR: {pr_id}")
        ])

    def enrich_context(self, state: WorkflowState) -> dict:
        logger.info("Enriching context...")
        context = state.context

        return {
            "repo": context.repo_name,
            "pr_id": context.pr_id,
            "author": context.author,
            "files_analyzed": len(context.code_snippets),
            "languages": list(set(s.language for s in context.code_snippets))
        }

    def update_severity(self, context_key: str, issue_ids: list, severity_adjust: int):
        if not issue_ids or not isinstance(issue_ids, list):
            raise ValueError("issue_ids must be a non-empty list")

        try:
            history = self.memory.load_memory_variables({"prompt": context_key})
            updated_history = []

            for record in history:
                if isinstance(record, str):
                    try:
                        record = json.loads(record)
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON in memory record: {str(e)}")
                        continue

                for issue in record.get("issues", []):
                    if issue.get("id") in issue_ids:
                        current_sev = issue.get("severity", 2)
                        issue["severity"] = max(1, min(4, current_sev + severity_adjust))

                updated_history.append(record)

            self.memory.save_context(
                {"input": context_key},
                {"output": json.dumps(updated_history)}
            )

            self.vector_store.persist()

            if not os.path.exists("memory_store"):
                raise RuntimeError("Failed to persist memory store")

        except Exception as e:
            logger.error(f"Failed to update severity for context '{context_key}': {str(e)}")
            raise

    def _analyze_commit_history(self, history: list) -> str:
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
            )
        }

        return "\n".join([f"{k}: {v} occurrences" for k, v in patterns.items()])
