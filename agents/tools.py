import os
import re
import difflib
import hashlib
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEndpoint
from langchain_core.output_parsers import JsonOutputParser


class FreeLLMProvider:
    def __init__(self, provider="gemini"):
        self.provider = provider
        self.models = self._get_model_mapping()

    def _get_model_mapping(self):
        return {
            "gemini": {
                "security": "gemini-1.5-flash",
                "quality": "gemini-1.5-flash",
                "logic": "gemini-1.5-flash",
                "context": "gemini-1.5-pro",
                "decision": "gemini-1.5-pro"
            },
            "groq": {
                "security": "llama3-70b-8192",
                "quality": "llama3-8b-8192",
                "logic": "llama3-8b-8192",
                "context": "llama3-70b-8192",
                "decision": "llama3-70b-8192"
            },
            "huggingface": {
                "security": "microsoft/DialoGPT-medium",
                "quality": "microsoft/DialoGPT-medium",
                "logic": "microsoft/DialoGPT-medium",
                "context": "microsoft/DialoGPT-medium",
                "decision": "microsoft/DialoGPT-medium"
            }
        }

    def get_llm(self, agent_type: str, temperature: float = 0.2):
        model_name = self.models[self.provider][agent_type]

        if self.provider == "gemini":
            return ChatGoogleGenerativeAI(
                google_api_key=os.getenv("GOOGLE_API_KEY"),
                model=model_name,
                temperature=temperature,
                max_tokens=4096,
                convert_system_message_to_human=True
            )
        elif self.provider == "groq":
            return ChatGroq(
                groq_api_key=os.getenv("GROQ_API_KEY"),
                model_name=model_name,
                temperature=temperature,
                max_tokens=4096
            )
        elif self.provider == "huggingface":
            return HuggingFaceEndpoint(
                huggingfacehub_api_token=os.getenv("HUGGINGFACE_API_TOKEN"),
                repo_id=model_name,
                temperature=temperature,
                max_length=2048
            )
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")


def get_llm(agent_type: str, provider: str = "gemini", temperature: float = 0.2):
    return FreeLLMProvider(provider).get_llm(agent_type, temperature=temperature)


def parse_code_blocks(response: str) -> list:
    """Extract code blocks from markdown-style LLM responses."""
    pattern = r"```[\w]*\n(.*?)\n```"
    return re.findall(pattern, response, re.DOTALL)


def hash_content(content: str) -> str:
    """Hash content string using SHA-256."""
    return hashlib.sha256(content.encode()).hexdigest()


def create_parser(model):
    """Create a JSON parser for a Pydantic model."""
    return JsonOutputParser(pydantic_object=model)


def filter_high_severity(issues: list, min_severity="medium") -> list:
    """Filter issues by minimum severity level."""
    severity_levels = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    min_level = severity_levels.get(min_severity, 2)
    return [
        issue for issue in issues
        if severity_levels.get(getattr(issue, 'severity', 'low').lower(), 0) >= min_level
    ]


def generate_patch(issue: dict, context) -> dict:
    """Generate a patch for auto-fixable issues using heuristics."""
    try:
        file_path = issue.get("file")
        snippet = next((s for s in context.code_snippets if s.file_path == file_path), None)
        if not snippet:
            return None

        content = snippet.content.splitlines()
        line_num = issue.get("line", 0) - 1
        if line_num >= len(content) or line_num < 0:
            return None

        original_line = content[line_num]
        fix = None

        if issue["type"] == "Hardcoded Secret":
            match = re.findall(r"['\"](.*?)['\"]", original_line)
            if match:
                secret = match[0]
                content[line_num] = original_line.replace(secret, "os.getenv('SECRET_KEY')")
                fix = "Replaced hardcoded secret with environment variable"

        elif issue["type"] == "SQL Injection":
            if "?" not in original_line:
                content[line_num] = original_line.replace(")", ", ?)")
                fix = "Parameterized SQL query"

        else:
            return None

        diff = list(difflib.unified_diff(
            snippet.content.splitlines(),
            content,
            fromfile=file_path,
            tofile=file_path,
            lineterm=""
        ))

        return {
            "file": file_path,
            "patch": "\n".join(diff),
            "fix_description": fix
        }

    except Exception:
        return None



'''
Works seamlessly with your agents (ContextAgent, DecisionAgent, etc.)
Can auto-fix:
Unparameterized SQL queries → adds ? for placeholders
Filters high/critical severity issues for prioritization
Dynamically loads the right model based on agent type and provider
'''