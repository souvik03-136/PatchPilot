from typing import List, Dict, Any, Optional, Annotated
from pydantic import BaseModel, Field
import operator

# ✅ Represents a snippet of source code for analysis
class CodeSnippet(BaseModel):
    file_path: str
    content: str
    language: str

# ✅ Represents a security issue detected in the code
class Vulnerability(BaseModel):
    type: str
    severity: str = "medium"  # low | medium | high | critical
    description: str
    line: int
    file: str
    confidence: float = 0.8

# ✅ Represents a code quality issue (e.g., style, complexity)
class QualityIssue(BaseModel):
    type: str
    description: str
    line: int
    file: str
    severity: str = "low"
    rule_id: Optional[str] = None

# ✅ Shared context across all analysis agents (e.g., repo metadata, history)
class AnalysisContext(BaseModel):
    repo_name: str = "unknown"
    pr_id: str = "unknown"
    author: str = "unknown"
    commit_history: List[Dict] = Field(default_factory=list)  # e.g., list of commit dicts
    previous_issues: List[Vulnerability] = Field(default_factory=list)  # historical issues
    code_snippets: List[CodeSnippet] = Field(default_factory=list)  # target code files for analysis
    agent_memory: Dict[str, Any] = Field(default_factory=dict)  # optional persistent state

# ✅ Generic response wrapper returned by agents
class AgentResponse(BaseModel):
    success: bool
    results: List[Any] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    next_steps: List[str] = Field(default_factory=list)

# ✅ Main state structure used in LangGraph StateGraph
class WorkflowState(BaseModel):
    context: AnalysisContext
    # ✅ Using operator.add for parallel-safe updates
    security_results: Annotated[List[Vulnerability], operator.add] = []
    quality_results: Annotated[List[QualityIssue], operator.add] = []
    logic_results: Annotated[List[Any], operator.add] = []
    enriched_context: Dict[str, Any] = Field(default_factory=dict)
    decision: Dict[str, Any] = Field(default_factory=dict)