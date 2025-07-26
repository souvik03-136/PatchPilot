import json
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from .models import QualityIssue, WorkflowState
from .tools import FreeLLMProvider


class QualityAgent:
    def __init__(self, provider: str = "gemini"):
        self.llm_provider = FreeLLMProvider(provider)
        self.llm = self.llm_provider.get_llm("quality")
        self.parser = StrOutputParser()

        self.prompt = ChatPromptTemplate.from_messages([
            ("user", """You are a code quality expert. Review this code for quality issues:

File: {file_path}
Code:
{code}

Check for:
1. Style violations (PEP8, naming conventions)
2. Code complexity (long functions, deep nesting)
3. Missing documentation
4. Code duplication
5. Error handling issues
6. Performance problems
7. Maintainability issues

For each issue found, respond with JSON format:
[
    {
        "type": "quality_issue_type",
        "description": "detailed description",
        "line": line_number,
        "file": "filename",
        "severity": "low/medium/high",
        "rule_id": "optional_rule_id"
    }
]

If no issues found, return: []

Response (JSON only):""")
        ])

    def _create_chain(self):
        return self.prompt | self.llm | self.parser

    def analyze(self, state: WorkflowState) -> WorkflowState:
        """Analyze code snippets for quality issues and update WorkflowState."""
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
                                QualityIssue(
                                    type=item.get("type", "Quality Issue"),
                                    description=item.get("description", ""),
                                    line=item.get("line", 0),
                                    file=item.get("file", snippet.file_path),
                                    severity=item.get("severity", "low"),
                                    rule_id=item.get("rule_id")
                                )
                            )

                except json.JSONDecodeError:
                    if any(word in response.lower() for word in ["style", "complexity", "documentation", "error"]):
                        results.append(
                            QualityIssue(
                                type="Code Quality Issue",
                                description=response[:200] + "..." if len(response) > 200 else response,
                                line=0,
                                file=snippet.file_path,
                                severity="low"
                            )
                        )

            except Exception as e:
                file_path = getattr(snippet, "file_path", "unknown")
                errors.append(f"Error analyzing {file_path}: {str(e)}")

        #  Update WorkflowState
        state.quality_results = results
        state.quality_errors = errors
        return state
