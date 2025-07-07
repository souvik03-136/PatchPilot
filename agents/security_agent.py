# security_agent.py - Using Free LLMs
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from .models import Vulnerability, AgentResponse
from .tools import FreeLLMProvider
import json

class SecurityAgent:
    def __init__(self, provider: str = "gemini"):
        self.llm_provider = FreeLLMProvider(provider)
        self.llm = self.llm_provider.get_llm("security")
        self.parser = StrOutputParser()
        
        # Simplified prompt for better free model performance
        self.prompt = ChatPromptTemplate.from_messages([
            ("user", """You are a security expert. Analyze this code for security vulnerabilities:

File: {file_path}
Code:
{code}

Find these security issues:
1. Hardcoded passwords/secrets/API keys
2. SQL injection vulnerabilities
3. XSS vulnerabilities
4. Insecure file operations
5. Authentication bypass
6. Command injection
7. Path traversal
8. Insecure randomness
9. Weak encryption
10. Missing input validation

For each vulnerability found, respond with JSON format:
[
    {{
        "type": "vulnerability_type",
        "severity": "low/medium/high/critical",
        "description": "detailed description",
        "line": line_number,
        "file": "filename",
        "confidence": confidence_score
    }}
]

If no vulnerabilities found, return: []

Response (JSON only):""")
        ])

    def analyze(self, code_snippets: list) -> AgentResponse:
        results = []
        errors = []
        
        for snippet in code_snippets:
            try:
                # Create chain and invoke
                chain = self.prompt | self.llm | self.parser
                response = chain.invoke({
                    "file_path": snippet.file_path,
                    "code": snippet.content
                })
                
                # Parse JSON response
                try:
                    # Clean response - remove markdown formatting
                    clean_response = response.strip()
                    if clean_response.startswith("```json"):
                        clean_response = clean_response[7:]
                    if clean_response.endswith("```"):
                        clean_response = clean_response[:-3]
                    
                    # Parse JSON
                    analysis = json.loads(clean_response.strip())
                    
                    # Convert to Vulnerability objects
                    for item in analysis:
                        if isinstance(item, dict):
                            vulnerability = Vulnerability(
                                type=item.get("type", "Unknown"),
                                severity=item.get("severity", "medium"),
                                description=item.get("description", ""),
                                line=item.get("line", 0),
                                file=item.get("file", snippet.file_path),
                                confidence=item.get("confidence", 0.8)
                            )
                            results.append(vulnerability)
                            
                except json.JSONDecodeError:
                    # Fallback: extract basic info from text response
                    if "vulnerability" in response.lower() or "security" in response.lower():
                        vulnerability = Vulnerability(
                            type="Potential Security Issue",
                            severity="medium",
                            description=response[:200] + "..." if len(response) > 200 else response,
                            line=0,
                            file=snippet.file_path,
                            confidence=0.6
                        )
                        results.append(vulnerability)
                    
            except Exception as e:
                errors.append(f"Error analyzing {snippet.file_path}: {str(e)}")
        
        return AgentResponse(
            success=len(errors) == 0,
            results=results,
            errors=errors,
            metadata={"total_files": len(code_snippets), "issues_found": len(results)}
        )
