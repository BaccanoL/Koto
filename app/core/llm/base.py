from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Generator

class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    Standardizes the interface for OpenAI, Google Gemini, Anthropic, Ollama, etc.
    """
    
    @abstractmethod
    def generate_content(
        self, 
        prompt: Union[str, List[Dict[str, Any]]],
        model: str,
        system_instruction: Optional[str] = None,
        tools: Optional[List[Any]] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[Dict[str, Any], Generator[Dict[str, Any], None, None]]:
        """
        Generate content from the LLM.
        
        Args:
            prompt: The user prompt or list of messages
            model: Model identifier
            system_instruction: System prompt
            tools: List of tool definitions
            stream: Whether to stream the response
            **kwargs: Additional provider-specific arguments (temperature, etc.)
            
        Returns:
            Structured response dictionary or generator if streaming
        """
        pass
        
    @abstractmethod
    def get_token_count(self, prompt: Union[str, List[Dict[str, Any]]], model: str) -> int:
        """Count tokens for a given prompt/model"""
        pass
