from langchain_core.prompts import ChatPromptTemplate
from langchain.memory import ConversationBufferMemory
from .models import AnalysisContext, AgentResponse
from .tools import get_llm, hash_content

class ContextAgent:
    def __init__(self, model: str = "codellama:13b"):
        self.llm = get_llm(model)
        self.memory = ConversationBufferMemory()
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a context manager. Your tasks:
            1. Maintain developer profiles
            2. Correlate current findings with historical data
            3. Identify recurring issues
            4. Adjust severity based on context
            5. Maintain agent memory
            
            Current context:
            - Repo: {repo_name}
            - PR: {pr_id}
            - Author: {author}
            
            Previous issues: {previous_issues}
            
            Respond with enriched context in JSON format."""),
            ("human", "Enrich analysis context with historical data")
        ])

    def enrich_context(self, context: AnalysisContext) -> AgentResponse:
        try:
            # Create memory key for this author/repo
            memory_key = f"{context.repo_name}:{hash_content(context.author)}"
            
            # Retrieve historical context
            history = self.memory.load_memory_variables({}).get(memory_key, "")
            
            # Prepare prompt
            prompt = self.prompt.format(
                repo_name=context.repo_name,
                pr_id=context.pr_id,
                author=context.author,
                previous_issues=str(context.previous_issues[:3]),  # Show recent issues
                history=history
            )
            
            # Get enriched context
            response = self.llm.invoke(prompt)
            
            # Update memory
            self.memory.save_context(
                {"input": prompt},
                {"output": response}
            )
            
            return AgentResponse(
                success=True,
                results=[response],
                metadata={"memory_key": memory_key}
            )
        except Exception as e:
            return AgentResponse(
                success=False,
                errors=[f"Context enrichment failed: {str(e)}"]
            )