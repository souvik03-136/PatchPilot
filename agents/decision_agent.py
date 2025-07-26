import json
from .models import WorkflowState
from .tools import get_llm
from langchain_core.prompts import ChatPromptTemplate

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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

    def make_decision(self, state: WorkflowState) -> WorkflowState:
        """Update WorkflowState with the decision based on analysis results."""
        critical_issues = [i for i in state.security_results if i.severity == "critical"]
        high_issues = [i for i in state.security_results if i.severity == "high"]

        if critical_issues:
            decision_data = {
                "decision": "BLOCK",
                "risk_level": "critical",
                "summary": f"{len(critical_issues)} critical issues found"
            }
        elif len(high_issues) > 3:
            decision_data = {
                "decision": "BLOCK",
                "risk_level": "high",
                "summary": f"{len(high_issues)} high severity issues (>3)"
            }
        elif high_issues:
            decision_data = {
                "decision": "REQUEST_CHANGES",
                "risk_level": "high",
                "summary": f"{len(high_issues)} high severity issues"
            }
        else:
            decision_data = {
                "decision": "APPROVE",
                "risk_level": "low",
                "summary": "No critical issues found"
            }

        state.decision = decision_data
        return state

    def _parse_response(self, response: str) -> dict:
        """Parse LLM response into structured data."""
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
                return json.loads(json_str)
            elif "{" in response:
                return json.loads(response)
            else:
                raise ValueError("No valid JSON found")
        except (json.JSONDecodeError, ValueError):
            return {
                "decision": "BLOCK" if "critical" in response.lower() else "REQUEST_CHANGES",
                "summary": response[:200],
                "auto_fix_issues": [],
                "critical_issues": []
            }
