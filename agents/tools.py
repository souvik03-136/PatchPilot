import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEndpoint
from langchain_core.output_parsers import JsonOutputParser
import re
import hashlib

class FreeLLMProvider:
    def __init__(self, provider="gemini"):
        self.provider = provider
        self.models = self._get_model_mapping()
    
    def _get_model_mapping(self):
        return {
            "gemini": {
                "security": "gemini-1.5-flash",      # Fast and free
                "quality": "gemini-1.5-flash",       # Good for code quality
                "logic": "gemini-1.5-flash",         # Fast for logic analysis
                "context": "gemini-1.5-pro",        # More powerful for context
                "decision": "gemini-1.5-pro"        # Best for decisions
            },
            "groq": {
                "security": "llama3-70b-8192",      # Free Llama 3 70B
                "quality": "llama3-8b-8192",        # Free Llama 3 8B
                "logic": "llama3-8b-8192",          # Free Llama 3 8B
                "context": "llama3-70b-8192",       # Free Llama 3 70B
                "decision": "llama3-70b-8192"       # Free Llama 3 70B
            },
            "huggingface": {
                "security": "microsoft/DialoGPT-medium",
                "quality": "microsoft/DialoGPT-medium",
                "logic": "microsoft/DialoGPT-medium",
                "context": "microsoft/DialoGPT-medium",
                "decision": "microsoft/DialoGPT-medium"
            }
        }
    
    def get_llm(self, agent_type: str, temperature: float = 0.2):
        model_name = self.models[self.provider][agent_type]
        
        if self.provider == "gemini":
            return ChatGoogleGenerativeAI(
                google_api_key=os.getenv("GOOGLE_API_KEY"),
                model=model_name,
                temperature=temperature,
                max_tokens=4096,
                convert_system_message_to_human=True  # Gemini compatibility
            )
        elif self.provider == "groq":
            return ChatGroq(
                groq_api_key=os.getenv("GROQ_API_KEY"),
                model_name=model_name,
                temperature=temperature,
                max_tokens=4096
            )
        elif self.provider == "huggingface":
            return HuggingFaceEndpoint(
                huggingfacehub_api_token=os.getenv("HUGGINGFACE_API_TOKEN"),
                repo_id=model_name,
                temperature=temperature,
                max_length=2048
            )
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

def parse_code_blocks(response: str) -> list:
    pattern = r"```[\w]*\n(.*?)\n```"
    return re.findall(pattern, response, re.DOTALL)

def hash_content(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()

def create_parser(model):
    return JsonOutputParser(pydantic_object=model)

def filter_high_severity(issues: list, min_severity="medium") -> list:
    severity_levels = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    min_level = severity_levels.get(min_severity, 2)
    return [issue for issue in issues if severity_levels.get(getattr(issue, 'severity', 'low'), 0) >= min_level]
