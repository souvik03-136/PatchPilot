from langgraph.pregel import Graph
from langgraph.graph import END
from .models import WorkflowState

def create_analysis_workflow(agents: dict):
    workflow = Graph()
    
    # Define nodes
    workflow.add_node("security_analysis", agents["security"].analyze)
    workflow.add_node("quality_analysis", agents["quality"].analyze)
    workflow.add_node("logic_analysis", agents["logic"].analyze)
    workflow.add_node("enrich_context", agents["context"].enrich_context)
    workflow.add_node("make_decision", agents["decision"].make_decision)
    
    # Set entry points (run security, quality, logic in parallel)
    workflow.set_entry_point("security_analysis")
    workflow.set_entry_point("quality_analysis")
    workflow.set_entry_point("logic_analysis")
    
    # After parallel analysis, enrich context
    workflow.add_edge("security_analysis", "enrich_context")
    workflow.add_edge("quality_analysis", "enrich_context")
    workflow.add_edge("logic_analysis", "enrich_context")
    
    # Then make decision
    workflow.add_edge("enrich_context", "make_decision")
    workflow.add_edge("make_decision", END)
    
    # Handle state
    def update_state(state: WorkflowState, node: str, result: dict):
        if node == "security_analysis":
            state.security_results = result.get("results", [])
        elif node == "quality_analysis":
            state.quality_results = result.get("results", [])
        elif node == "logic_analysis":
            state.logic_results = result.get("results", [])
        elif node == "enrich_context":
            state.enriched_context = result.get("results", [])[0] if result.get("results") else {}
        elif node == "make_decision":
            state.decision = result.get("results", [])[0] if result.get("results") else {}
        return state
    
    # Compile workflow
    return workflow.compile(update_state=update_state)
