import json
import os
from .workflows import create_analysis_workflow
from .models import WorkflowState, AnalysisContext
from .security_agent import SecurityAgent
from .quality_agent import QualityAgent
from .logic_agent import LogicAgent
from .context_agent import ContextAgent
from .decision_agent import DecisionAgent

class AgentSystem:
    def __init__(self, provider: str = "gemini"):
        self.provider = provider
        self.agents = {
            "security": SecurityAgent(provider),
            "quality": QualityAgent(provider),
            "logic": LogicAgent(provider),
            "context": ContextAgent(provider),
            "decision": DecisionAgent(provider)
        }
        # Uncomment to use workflow-based execution
        # self.workflow = create_analysis_workflow(self.agents)

    def analyze_pull_request(self, context: AnalysisContext):
        results = {
            "security_issues": [],
            "quality_issues": [],
            "logic_issues": [],
            "decision": {},
            "context": {}
        }

        try:
            security_response = self.agents["security"].analyze(context.code_snippets)
            results["security_issues"] = security_response.results

            quality_response = self.agents["quality"].analyze(context.code_snippets)
            results["quality_issues"] = quality_response.results

            logic_response = self.agents["logic"].analyze(context.code_snippets)
            results["logic_issues"] = logic_response.results

            critical_security = sum(1 for i in results["security_issues"] if i.severity == "critical")
            high_security = sum(1 for i in results["security_issues"] if i.severity == "high")

            if critical_security > 0:
                decision = "BLOCK"
                risk_level = "CRITICAL"
            elif high_security > 2:
                decision = "REQUEST_CHANGES"
                risk_level = "HIGH"
            elif high_security > 0 or len(results["security_issues"]) > 3:
                decision = "REQUEST_CHANGES"
                risk_level = "MEDIUM"
            else:
                decision = "APPROVE"
                risk_level = "LOW"

            results["decision"] = {
                "decision": decision,
                "risk_level": risk_level,
                "summary": f"Found {len(results['security_issues'])} security issues, "
                           f"{len(results['quality_issues'])} quality issues",
                "critical_issues": critical_security,
                "total_issues": len(results["security_issues"]) + len(results["quality_issues"])
            }

        except Exception as e:
            results["error"] = str(e)

        return results

    def get_agent_status(self):
        return {
            "provider": self.provider,
            "agents": {name: "active" for name in self.agents.keys()}
        }

    def record_feedback(self, pr_id: str, feedback: dict) -> bool:
        """Record developer feedback to improve agents."""
        try:
            os.makedirs("feedback", exist_ok=True)
            feedback_file = f"feedback/{pr_id}.json"
            with open(feedback_file, "w") as f:
                json.dump(feedback, f)

            if feedback.get("accepted_issues"):
                self.agents["context"].update_severity(
                    context_key=feedback["pr_context"],
                    issue_ids=feedback["accepted_issues"],
                    severity_adjust=-1
                )

            if feedback.get("rejected_issues"):
                self.agents["context"].update_severity(
                    context_key=feedback["pr_context"],
                    issue_ids=feedback["rejected_issues"],
                    severity_adjust=1
                )

            return True
        except Exception as e:
            print(f"Feedback recording failed: {str(e)}")
            return False
