from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class CodeSnippet(BaseModel):
    file_path: str
    content: str
    language: str

class Vulnerability(BaseModel):
    type: str
    severity: str = "medium"  # low, medium, high, critical
    description: str
    line: int
    file: str
    confidence: float = 0.8

class QualityIssue(BaseModel):
    type: str
    description: str
    line: int
    file: str
    severity: str = "low"
    rule_id: Optional[str] = None

class AnalysisContext(BaseModel):
    repo_name: str
    pr_id: str
    author: str
    commit_history: List[Dict]
    previous_issues: List[Vulnerability]
    code_snippets: List[CodeSnippet]
    agent_memory: Dict[str, Any] = {}

class AgentResponse(BaseModel):
    success: bool
    results: List[Any]
    errors: List[str] = []
    metadata: Dict[str, Any] = {}
    next_steps: List[str] = []

class WorkflowState(BaseModel):
    context: AnalysisContext
    security_results: List[Vulnerability] = []
    quality_results: List[QualityIssue] = []
    logic_results: List[Any] = []
    enriched_context: Dict[str, Any] = {}
    decision: Dict[str, Any] = {}