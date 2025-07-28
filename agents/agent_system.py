import json
import os
import sys
import signal
import time
from contextlib import contextmanager
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
    if sys.platform == "win32":
        # Windows fallback: manual timing
        start = time.time()
        yield
        if time.time() - start > seconds:
            raise TimeoutException("Timed out!")
    else:
        def signal_handler(signum, frame):
            raise TimeoutException("Timed out!")
        signal.signal(signal.SIGALRM, signal_handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)


class AgentSystem:
    def __init__(self, provider: str = "gemini", device: str = "cpu"):  # fixed constructor typo
        self.provider = provider
        self.device = device
        self.agents = {
            "security": SecurityAgent(provider),
            "quality": QualityAgent(provider),
            "logic": LogicAgent(provider),
            "context": ContextAgent(provider, device=device),
            "decision": DecisionAgent(provider)
        }

    def analyze_pull_request(self, context: AnalysisContext):
        """Run PR analysis manually with detailed logging."""
        print("Starting workflow analysis...")
        print(f"Code snippets: {len(context.code_snippets)}")

        state = WorkflowState(context=context)
        print("Initial state created")

        try:
            with time_limit(120):
                # --- Security Agent ---
                print("\n--- Executing Security Agent ---")
                security_response = self.agents["security"].analyze(state)
                state.security_results = security_response.results
                print(f"Security issues found: {len(state.security_results)}")

                # --- Quality Agent ---
                print("\n--- Executing Quality Agent ---")
                quality_response = self.agents["quality"].analyze(state)
                state.quality_results = quality_response.results
                print(f"Quality issues found: {len(state.quality_results)}")

                # --- Logic Agent ---
                print("\n--- Executing Logic Agent ---")
                logic_response = self.agents["logic"].analyze(state)
                state.logic_results = logic_response.results
                print(f"Logic issues found: {len(state.logic_results)}")

                # --- Context Agent ---
                print("\n--- Executing Context Agent ---")
                context_result = self.agents["context"].enrich_context(state)
                state.enriched_context = context_result
                print("Context enriched")

                # --- Decision Agent ---
                print("\n--- Executing Decision Agent ---")
                decision_result = self.agents["decision"].make_decision(state)
                state.decision = decision_result
                print(f"Final decision: {state.decision.get('decision', 'UNKNOWN')}")

                return {
                    "security_issues": state.security_results,
                    "quality_issues": state.quality_results,
                    "logic_issues": state.logic_results,
                    "decision": state.decision,
                    "context": state.enriched_context,
                    "errors": {
                        "security": security_response.errors,
                        "quality": quality_response.errors,
                        "logic": logic_response.errors
                    }
                }

        except TimeoutException:
            print("Workflow error: Timed out after 2 minutes")
            return {"error": "Analysis timed out after 2 minutes"}
        except Exception as e:
            print(f"Workflow error: {str(e)}")
            return {"error": str(e)}

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
