import json
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from .models import QualityIssue, AgentResponse
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
    {{
        "type": "quality_issue_type",
        "description": "detailed description",
        "line": line_number,
        "file": "filename",
        "severity": "low/medium/high",
        "rule_id": "optional_rule_id"
    }}
]

If no issues found, return: []

Response (JSON only):""")
        ])

    def analyze(self, state) -> AgentResponse:
        # ✅ Safely convert state to a dict
        state_dict = dict(state)
        code_snippets = state_dict.get("code_snippets", [])

        results = []
        errors = []

        for snippet in code_snippets:
            try:
                # Defensive handling for tuple input like (index, snippet)
                if isinstance(snippet, tuple):
                    snippet = snippet[1]

                chain = self.prompt | self.llm | self.parser
                response = chain.invoke({
                    "file_path": snippet.file_path,
                    "code": snippet.content
                })

                # Parse JSON response
                try:
                    clean_response = response.strip()
                    if clean_response.startswith("```json"):
                        clean_response = clean_response[7:]
                    if clean_response.endswith("```"):
                        clean_response = clean_response[:-3]

                    analysis = json.loads(clean_response.strip())

                    for item in analysis:
                        if isinstance(item, dict):
                            issue = QualityIssue(
                                type=item.get("type", "Quality Issue"),
                                description=item.get("description", ""),
                                line=item.get("line", 0),
                                file=item.get("file", snippet.file_path),
                                severity=item.get("severity", "low"),
                                rule_id=item.get("rule_id")
                            )
                            results.append(issue)

                except json.JSONDecodeError:
                    if any(word in response.lower() for word in ["style", "complexity", "documentation", "error"]):
                        issue = QualityIssue(
                            type="Code Quality Issue",
                            description=response[:200] + "..." if len(response) > 200 else response,
                            line=0,
                            file=snippet.file_path,
                            severity="low"
                        )
                        results.append(issue)

            except Exception as e:
                file_path = getattr(snippet, "file_path", "unknown")
                errors.append(f"Error analyzing {file_path}: {str(e)}")

        return AgentResponse(
            success=len(errors) == 0,
            results=results,
            errors=errors,
            metadata={
                "total_files": len(code_snippets),
                "issues_found": len(results)
            }
        )
