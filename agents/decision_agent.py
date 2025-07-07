from langchain_core.prompts import ChatPromptTemplate
from .models import AgentResponse, Vulnerability, QualityIssue
from .tools import get_llm, filter_high_severity

class DecisionAgent:
    def __init__(self, model: str = "codellama:34b"):
        self.llm = get_llm(model)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a decision agent. Your responsibilities:
            1. Risk assessment of PR
            2. Merge decision (approve, block, request changes)
            3. Generate developer report
            4. Suggest fixes for critical issues
            5. Plan next actions
            
            Security issues: {security_issues}
            Quality issues: {quality_issues}
            Logic issues: {logic_issues}
            Context: {context}
            
            Respond in JSON format with:
            - decision: APPROVE|BLOCK|REQUEST_CHANGES
            - risk_level: LOW|MEDIUM|HIGH|CRITICAL
            - summary: string
            - critical_issues: list
            - suggested_fixes: list
            - next_steps: list"""),
            ("human", "Make a decision for PR: {pr_id}")
        ])

    def make_decision(self, state: dict) -> AgentResponse:
        try:
            # Filter critical security issues
            critical_issues = filter_high_severity(
                state.get("security_results", []), 
                "high"
            )
            
            # Prepare prompt
            prompt = self.prompt.format(
                pr_id=state["context"].pr_id,
                security_issues=str(state.get("security_results", [])[:3]),
                quality_issues=str(state.get("quality_results", [])[:3]),
                logic_issues=str(state.get("logic_results", [])[:1]),
                context=str(state.get("enriched_context", {}))
            )
            
            # Get decision
            response = self.llm.invoke(prompt)
            
            return AgentResponse(
                success=True,
                results=[response],
                metadata={"critical_issues": critical_issues}
            )
        except Exception as e:
            return AgentResponse(
                success=False,
                errors=[f"Decision failed: {str(e)}"]
            )