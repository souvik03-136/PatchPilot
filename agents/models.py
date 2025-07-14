from typing import List, Dict, Any, Optional, Annotated
from pydantic import BaseModel, Field
import operator


class CodeSnippet(BaseModel):
    """Represents a snippet of source code for analysis."""
    file_path: str
    content: str
    language: str


class Vulnerability(BaseModel):
    """Represents a security issue detected in the code."""
    type: str
    severity: str = "medium"  # low | medium | high | critical
    description: str
    line: int
    file: str
    confidence: float = 0.8


class QualityIssue(BaseModel):
    """Represents a code quality issue (e.g., style, complexity)."""
    type: str
    description: str
    line: int
    file: str
    severity: str = "low"
    rule_id: Optional[str] = None


class AnalysisContext(BaseModel):
    """Shared context across all analysis agents (e.g., repo metadata, history)."""
    repo_name: str = "unknown"
    pr_id: str = "unknown"
    author: str = "unknown"
    commit_history: List[Dict] = Field(default_factory=list)
    previous_issues: List[Vulnerability] = Field(default_factory=list)
    code_snippets: List[CodeSnippet] = Field(default_factory=list)
    agent_memory: Dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    """Generic response wrapper returned by agents."""
    success: bool
    results: List[Any] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    next_steps: List[str] = Field(default_factory=list)


class WorkflowState(BaseModel):
    """Main state structure used in LangGraph StateGraph."""
    context: AnalysisContext
    security_results: Annotated[List[Vulnerability], operator.add] = []
    quality_results: Annotated[List[QualityIssue], operator.add] = []
    logic_results: Annotated[List[Any], operator.add] = []
    enriched_context: Dict[str, Any] = Field(default_factory=dict)
    decision: Dict[str, Any] = Field(default_factory=dict)
