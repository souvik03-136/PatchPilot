import json
from .models import AgentResponse
from .tools import get_llm, generate_patch
from langchain_core.prompts import ChatPromptTemplate


class DecisionAgent:
    def __init__(self, provider: str = "gemini"):
        self.llm = get_llm("decision", provider)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a decision agent. Evaluate:

Security Issues: {security_issues}
Quality Issues: {quality_issues}
Logic Issues: {logic_issues}
Context: {context}

Make decisions:
- APPROVE: Only trivial/non-critical issues
- REQUEST_CHANGES: Medium issues or <3 high issues
- BLOCK: Critical issues or >3 high issues

Generate remediation plan:
- Auto-fix trivial issues
- Suggest fixes for complex issues
- Block merge if critical"""),
            ("human", "Decide for PR: {pr_id}")
        ])

    def make_decision(self, state: dict) -> AgentResponse:
        try:
            # Format the LLM prompt input
            prompt = self.prompt.format(
                pr_id=state["context"].pr_id,
                security_issues=str(state.get("security_results", [])[:3]),
                quality_issues=str(state.get("quality_results", [])[:3]),
                logic_issues=str(state.get("logic_results", [])[:1]),
                context=str(state.get("enriched_context", {}))
            )

            # Invoke LLM
            response = self.llm.invoke(prompt)
            decision_data = self._parse_response(response)

            # Generate patches for auto-fixable issues
            patches = []
            for issue in decision_data.get("auto_fix_issues", []):
                patch = generate_patch(issue, state["context"])
                if patch:
                    patches.append(patch)

            return AgentResponse(
                success=True,
                results=[decision_data],
                patches=patches,
                metadata={"critical_issues": decision_data.get("critical_issues", [])}
            )
        except Exception as e:
            return AgentResponse(
                success=False,
                errors=[f"Decision failed: {str(e)}"]
            )

    def _parse_response(self, response: str) -> dict:
        """Parse LLM response into structured data."""
        try:
            # Handle JSON block in markdown
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
                return json.loads(json_str)
            elif "{" in response:
                return json.loads(response)
            else:
                raise ValueError("No valid JSON found")
        except (json.JSONDecodeError, ValueError):
            # Fallback: approximate decision
            return {
                "decision": "BLOCK" if "critical" in response.lower() else "REQUEST_CHANGES",
                "summary": response[:200],
                "auto_fix_issues": [],
                "critical_issues": []
            }


'''
Auto-remediation support via patch generation
Robust LLM response parsing (_parse_response)
LLM-based decision-making (APPROVE / REQUEST_CHANGES / BLOCK)
Metadata handling of critical issues
Exception safety
'''