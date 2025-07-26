import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from .models import Vulnerability, WorkflowState
from .tools import FreeLLMProvider


class SecurityAgent:
    def __init__(self, provider: str = "gemini"):
        self.llm_provider = FreeLLMProvider(provider)
        self.llm = self.llm_provider.get_llm("security")
        self.parser = StrOutputParser()

        self.prompt = ChatPromptTemplate.from_messages([
            ("user", """You are a security expert. Analyze this code for security vulnerabilities:

File: {file_path}
Code:
{code}

Find these security issues:
1. Hardcoded passwords/secrets/API keys
2. SQL injection vulnerabilities
3. XSS vulnerabilities
4. Insecure file operations
5. Authentication bypass
6. Command injection
7. Path traversal
8. Insecure randomness
9. Weak encryption
10. Missing input validation

For each vulnerability found, respond with JSON format:
[
    {{
        "type": "vulnerability_type",
        "severity": "low/medium/high/critical",
        "description": "detailed description",
        "line": line_number,
        "file": "filename",
        "confidence": confidence_score
    }}
]

If no vulnerabilities found, return: []

Response (JSON only):""")
        ])

    def _create_chain(self):
        """Create the LangChain chain for processing."""
        return self.prompt | self.llm | self.parser

    def analyze(self, state: WorkflowState) -> WorkflowState:
        """Analyze code snippets and update the WorkflowState."""
        context = state.context
        results = []
        errors = []

        for snippet in context.code_snippets:
            try:
                chain = self._create_chain()
                response = chain.invoke({
                    "file_path": snippet.file_path,
                    "code": snippet.content
                })

                clean_response = response.strip()
                if clean_response.startswith("```json"):
                    clean_response = clean_response[7:]
                if clean_response.endswith("```"):
                    clean_response = clean_response[:-3]

                try:
                    analysis = json.loads(clean_response.strip())
                    for item in analysis:
                        if isinstance(item, dict):
                            results.append(
                                Vulnerability(
                                    type=item.get("type", "Unknown"),
                                    severity=item.get("severity", "medium"),
                                    description=item.get("description", ""),
                                    line=item.get("line", 0),
                                    file=item.get("file", snippet.file_path),
                                    confidence=item.get("confidence", 0.8)
                                )
                            )

                except json.JSONDecodeError:
                    if "vulnerability" in response.lower() or "security" in response.lower():
                        results.append(
                            Vulnerability(
                                type="Potential Security Issue",
                                severity="medium",
                                description=response[:200] + "..." if len(response) > 200 else response,
                                line=0,
                                file=snippet.file_path,
                                confidence=0.6
                            )
                        )

            except Exception as e:
                file_path = getattr(snippet, "file_path", "unknown")
                errors.append(f"Error analyzing {file_path}: {str(e)}")

        state.security_results = results
        state.security_errors = errors
        return state
