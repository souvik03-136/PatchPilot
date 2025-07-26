import json
import os
import signal
from contextlib import contextmanager
from .workflows import create_analysis_workflow
from .models import WorkflowState, AnalysisContext
from .security_agent import SecurityAgent
from .quality_agent import QualityAgent
from .logic_agent import LogicAgent
from .context_agent import ContextAgent
from .decision_agent import DecisionAgent


class TimeoutException(Exception):
    """Custom exception for timeouts."""
    pass


@contextmanager
def time_limit(seconds):
    """Context manager to enforce a time limit on execution."""
    def signal_handler(signum, frame):
        raise TimeoutException("Timed out!")
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)


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
        # Create the workflow
        self.workflow = create_analysis_workflow(self.agents)

    def analyze_pull_request(self, context: AnalysisContext):
        """Analyze a pull request with a 2-minute timeout."""
        try:
            initial_state = WorkflowState(context=context)

            # ✅ Add timeout (2 minutes)
            with time_limit(120):
                final_state = self.workflow.invoke(initial_state)

            results = {
                "security_issues": final_state.security_results,
                "quality_issues": final_state.quality_results,
                "logic_issues": final_state.logic_results,
                "decision": final_state.decision,
                "context": final_state.enriched_context
            }

        except TimeoutException:
            return {"error": "Analysis timed out after 2 minutes"}
        except Exception as e:
            return {"error": str(e)}

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
