from langgraph.graph import StateGraph, END, START
from .models import WorkflowState


def route_based_on_severity(state: WorkflowState) -> str:
    """Route to decision making if critical issues found, otherwise enrich context"""
    critical = any(issue.severity == "critical" for issue in state.security_results)
    return "make_decision" if critical else "enrich_context"


def create_analysis_workflow(agents: dict):
    """Create the analysis workflow with parallel execution"""
    
    # 🛠️ Initialize workflow graph
    builder = StateGraph(WorkflowState)

    # ⏱️ Nodes for parallel analysis
    builder.add_node("security_analysis", agents["security"].analyze)
    builder.add_node("quality_analysis", agents["quality"].analyze)
    builder.add_node("logic_analysis", agents["logic"].analyze)

    # 📥 Post-processing nodes
    builder.add_node("enrich_context", agents["context"].enrich_context)
    builder.add_node("make_decision", agents["decision"].make_decision)

    # ▶️ Initial fan-out - start all analysis agents in parallel
    builder.add_edge(START, "security_analysis")
    builder.add_edge(START, "quality_analysis")
    builder.add_edge(START, "logic_analysis")

    # 🚦 Routing based on critical severity after all parallel nodes complete
    builder.add_conditional_edges(
        "security_analysis",
        route_based_on_severity,
        {
            "enrich_context": "enrich_context",
            "make_decision": "make_decision"
        }
    )
    
    # Wait for all parallel nodes to complete before routing
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

    # ✅ Final steps
    builder.add_edge("enrich_context", "make_decision")
    builder.add_edge("make_decision", END)

    return builder.compile()