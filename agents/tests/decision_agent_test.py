import os
import sys
import json
import time
from unittest.mock import patch, Mock, MagicMock

# Add root path so `agents` can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from agents.models import AgentResponse
from agents.decision_agent import DecisionAgent


class MockLLM:
    def __init__(self, response_text):
        self.response_text = response_text

    def invoke(self, prompt):
        return self.response_text


def create_mock_context():
    return type("MockContext", (), {
        "pr_id": "PR-789",
        "repo_name": "test-repo",
        "author": "jane.doe"
    })()


def create_test_state():
    return {
        "context": create_mock_context(),
        "security_results": [{"type": "SQL Injection", "severity": "high"}],
        "quality_results": [{"type": "Code Smell", "severity": "medium"}],
        "logic_results": [{"type": "Logic Flaw", "severity": "critical"}],
        "enriched_context": {"history": "Some context"}
    }


def test_decision_agent_initialization():
    print("Testing DecisionAgent initialization...")

    with patch("agents.decision_agent.get_llm") as mock_get_llm:
        mock_get_llm.return_value = Mock()
        agent = DecisionAgent(provider="gemini")

        assert agent.llm is not None
        assert agent.prompt is not None

        print("✓ DecisionAgent initialized successfully")


def test_make_decision_success():
    print("\nTesting make_decision with valid JSON response...")

    llm_response = json.dumps({
        "decision": "REQUEST_CHANGES",
        "summary": "Medium issues detected",
        "auto_fix_issues": [{"file": "main.py", "line": 10, "issue": "typo"}],
        "critical_issues": [{"file": "db.py", "line": 42, "issue": "SQL Injection"}]
    })

    with patch("agents.decision_agent.get_llm") as mock_get_llm, \
         patch("agents.decision_agent.generate_patch") as mock_generate_patch:

        mock_get_llm.return_value = MockLLM(llm_response)
        mock_generate_patch.return_value = {"file": "main.py", "patch": "---"}

        agent = DecisionAgent(provider="gemini")
        state = create_test_state()

        response = agent.make_decision(state)

        assert response.success is True
        assert response.results[0]["decision"] == "REQUEST_CHANGES"
        assert response.metadata["critical_issues"][0]["file"] == "db.py"

        print("✓ Decision made:", response.results[0]["decision"])


def test_make_decision_with_fallback_parsing():
    print("\nTesting make_decision with fallback response parsing...")

    fallback_text = "Critical vulnerability detected in db.py"

    with patch("agents.decision_agent.get_llm") as mock_get_llm:
        mock_get_llm.return_value = MockLLM(fallback_text)

        agent = DecisionAgent(provider="gemini")
        state = create_test_state()

        response = agent.make_decision(state)

        assert response.success is True
        assert response.results[0]["decision"] == "BLOCK"
        assert "summary" in response.results[0]

        print("✓ Fallback decision:", response.results[0]["decision"])


def test_parse_response_json_block_code():
    print("\nTesting _parse_response with markdown-style JSON...")

    response = """
    ```json
    {
        "decision": "APPROVE",
        "summary": "All good",
        "auto_fix_issues": [],
        "critical_issues": []
    }
    ```"""

    agent = DecisionAgent()
    data = agent._parse_response(response)

    assert data["decision"] == "APPROVE"
    assert data["summary"] == "All good"

    print("✓ Markdown JSON parsing passed")


def test_decision_patch_generation_skips_none():
    print("\nTesting patch generation skips None...")

    llm_response = json.dumps({
        "decision": "REQUEST_CHANGES",
        "auto_fix_issues": [{"file": "main.py", "line": 10, "issue": "fix spacing"}]
    })

    with patch("agents.decision_agent.get_llm") as mock_get_llm, \
         patch("agents.decision_agent.generate_patch") as mock_generate_patch:

        mock_get_llm.return_value = MockLLM(llm_response)
        mock_generate_patch.return_value = None  # simulate patch generation fail

        agent = DecisionAgent()
        response = agent.make_decision(create_test_state())

        assert response.success is True
        assert response.results[0]["decision"] == "REQUEST_CHANGES"

        print("✓ Patch generation safely handled None")


def test_decision_error_handling():
    print("\nTesting error handling during make_decision...")

    with patch("agents.decision_agent.get_llm") as mock_get_llm:
        mock_get_llm.return_value = Mock()
        mock_get_llm.return_value.invoke.side_effect = Exception("LLM crashed")

        agent = DecisionAgent()
        state = create_test_state()

        response = agent.make_decision(state)

        assert response.success is False
        assert "Decision failed" in response.errors[0]

        print("✓ Exception caught and handled correctly")


def main():
    print("=" * 60)
    print("DECISION AGENT UNIT TESTS")
    print("=" * 60)

    try:
        test_decision_agent_initialization()
        test_make_decision_success()
        test_make_decision_with_fallback_parsing()
        test_parse_response_json_block_code()
        test_decision_patch_generation_skips_none()
        test_decision_error_handling()

        print("\n" + "=" * 60)
        print("ALL DECISION AGENT TESTS PASSED")
        print("=" * 60)
    except Exception as e:
        print("\nTEST FAILED:", str(e))
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
