from langgraph.graph import StateGraph, END, START
from .models import WorkflowState



def route_based_on_severity(state: WorkflowState) -> str:
    """Route to decision making if critical issues are found, otherwise enrich context."""
    critical = any(issue.severity == "critical" for issue in state.security_results)
    return "make_decision" if critical else "enrich_context"


def create_analysis_workflow(agents: dict):
    """Create the analysis workflow with parallel execution."""
    builder = StateGraph(WorkflowState)

    # Agent analysis nodes
    builder.add_node("security_analysis", agents["security"].analyze)
    builder.add_node("quality_analysis", agents["quality"].analyze)
    builder.add_node("logic_analysis", agents["logic"].analyze)

    # Post-analysis nodes
    builder.add_node("enrich_context", agents["context"].enrich_context)
    builder.add_node("make_decision", agents["decision"].make_decision)

    # Initial fan-out: run analysis in parallel
    builder.add_edge(START, "security_analysis")
    builder.add_edge(START, "quality_analysis")
    builder.add_edge(START, "logic_analysis")

    # Conditional routing based on security severity
    builder.add_conditional_edges(
        "security_analysis",
        route_based_on_severity,
        {
            "enrich_context": "enrich_context",
            "make_decision": "make_decision"
        }
    )
    builder.add_conditional_edges(
        "quality_analysis",
        route_based_on_severity,
        {
            "enrich_context": "enrich_context",
            "make_decision": "make_decision"
        }
    )
    builder.add_conditional_edges(
        "logic_analysis",
        route_based_on_severity,
        {
            "enrich_context": "enrich_context",
            "make_decision": "make_decision"
        }
    )

    # Final transition
    builder.add_edge("enrich_context", "make_decision")
    builder.add_edge("make_decision", END)

    return builder.compile()