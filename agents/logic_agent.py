from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from .models import AgentResponse
from .tools import get_llm, parse_code_blocks, FreeLLMProvider


class LogicAgent:
    def __init__(self, provider: str = "gemini", llm=None):
        if llm is not None:
            self.llm = llm
        else:
            self.llm_provider = FreeLLMProvider(provider)
            self.llm = self.llm_provider.get_llm("logic")

        self.parser = StrOutputParser()

        self.prompt = ChatPromptTemplate.from_messages([
            ("user", """You are a logic analysis expert. Analyze this code for logical issues:

File: {file_path}
Code:
{code}

Look for:
1. Potential bugs and logical errors
2. Race conditions
3. Memory leaks
4. Null pointer exceptions
5. Infinite loops
6. Data flow issues
7. API contract violations
8. Edge case handling

Provide analysis in this format:
## Logic Analysis for {file_path}

### Issues Found:
1. **Issue Type**: Description
   - Line: X
   - Severity: Low/Medium/High
   - Fix: Suggested solution

### Suggestions:
- Suggestion 1
- Suggestion 2

If no issues found, state: "No logic issues detected."

Response:""")
        ])

    def _create_chain(self):
        """Create and return the prompt → LLM → parser chain."""
        return (
            RunnablePassthrough.assign(
                file_path=lambda x: x["file_path"],
                code=lambda x: x["code"]
            )
            | self.prompt
            | self.llm
            | self.parser
        )

    def analyze(self, state) -> AgentResponse:
        state_dict = dict(state)
        code_snippets = state_dict.get("code_snippets", [])

        results = []
        errors = []

        for snippet in code_snippets:
            try:
                if isinstance(snippet, tuple):
                    snippet = snippet[1]

                if not snippet or not snippet.content.strip():
                    raise ValueError("Empty code snippet")

                chain = self._create_chain()
                analysis = chain.invoke({
                    "file_path": snippet.file_path,
                    "code": snippet.content
                })

                code_blocks = parse_code_blocks(analysis)

                results.append({
                    "file": snippet.file_path,
                    "analysis": analysis,
                    "suggestions": code_blocks,
                    "has_issues": "no logic issues detected" not in analysis.lower()
                })

            except Exception as e:
                file_path = getattr(snippet, "file_path", "unknown")
                errors.append(f"Error analyzing {file_path}: {str(e)}")

        return AgentResponse(
            success=len(errors) == 0,
            results=results,
            errors=errors,
            metadata={
                "total_files": len(code_snippets),
                "analyses_completed": len(results)
            }
        )
