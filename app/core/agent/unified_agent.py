import logging
import time
import json
from typing import Any, Dict, Generator, List, Optional, Union

from app.core.agent.base import Agent
from app.core.agent.tool_registry import ToolRegistry
from app.core.agent.types import AgentStep, AgentStepType, AgentAction, AgentResponse
from app.core.llm.base import LLMProvider

logger = logging.getLogger(__name__)

class UnifiedAgent(Agent):
    """
    Unified Agent that supports ReAct loop and tool execution.
    Replaces web/agent_loop.py and web/adaptive_agent.py
    """
    
    MAX_STEPS = 15
    
    def __init__(
        self, 
        llm_provider: LLMProvider,
        tool_registry: Optional[ToolRegistry] = None,
        model_id: str = "gemini-3-flash-preview",
        system_instruction: Optional[str] = None
    ):
        super().__init__(llm_provider)
        self.registry = tool_registry or ToolRegistry()
        self.model_id = model_id
        self.base_system_instruction = system_instruction or (
            "You are Koto, an intelligent AI assistant. "
            "You can use tools to answer user questions. "
            "Think step-by-step. "
            "When the user asks about local machine status (CPU, memory, disk, network, processes, Python environment), "
            "prioritize calling available system info tools first, then explain results concisely. "
            "Do not guess live system metrics when tools are available."
        )

    def run(
        self, 
        input_text: str, 
        history: Optional[List[Dict]] = None,
        session_id: Optional[str] = None
    ) -> Generator[AgentStep, None, None]:
        """
        Executes the agent loop. Yields AgentStep objects to track progress.
        """
        steps_taken = 0
        current_history = list(history) if history else []
        
        # Add the user's initial input to history
        current_history.append({"role": "user", "content": input_text})
        
        # We need to maintain a provider-agnostic history structure.
        # LLMProvider implementations should handle conversion to specific API formats.
        # Here we use: {"role": "user"|"model"|"function", "content": str, "tool_calls": [...], "tool_id": ...}
        
        while steps_taken < self.MAX_STEPS:
            steps_taken += 1
            
            # Get tool definitions
            tools_def = self.registry.get_definitions()
            
            try:
                # Call LLM
                response = self.llm.generate_content(
                    prompt=current_history,
                    model=self.model_id,
                    system_instruction=self.base_system_instruction,
                    tools=tools_def if tools_def else None,
                    stream=False
                )
                
                content_text = response.get("content", "")
                tool_calls = response.get("tool_calls", [])
                
                # Yield Thought/Content if present
                if content_text:
                    yield AgentStep(
                        step_type=AgentStepType.THOUGHT, 
                        content=content_text
                    )
                    # Add thought to history
                    current_history.append({"role": "model", "content": content_text})

                # If no tool calls, we are done (Answer)
                if not tool_calls:
                    yield AgentStep(
                        step_type=AgentStepType.ANSWER,
                        content=content_text
                    )
                    break
                
                # Execute Tools
                for tool_call in tool_calls:
                    # tool_call format: {"name": str, "args": dict, "id": str (optional)}
                    tool_name = tool_call.get("name")
                    tool_args = tool_call.get("args", {})
                    # tool_id = tool_call.get("id") # OpenAI specific usually
                    
                    # Yield Action
                    action_obj = AgentAction(
                        tool_name=tool_name,
                        tool_args=tool_args,
                        tool_call_id=None 
                    )
                    yield AgentStep(
                        step_type=AgentStepType.ACTION,
                        content=f"Calling tool: {tool_name}",
                        action=action_obj
                    )
                    
                    # Store tool call in history (for provider to format)
                    # This is tricky without strict schema. We just append text for now to simulate conversation
                    # if the provider doesn't support structured history fully.
                    # But for Gemini, we rely on implicit handling or just state.
                    # Actually, for multi-turn tool use, we MUST provide correct history.
                    # Assuming LLMProvider can handle a list of dicts with 'tool_calls' key.
                    current_history.append({
                        "role": "model",
                        "content": "", # Empty content if just function call
                        "tool_calls": [tool_call]
                    })
                    
                    # Execute
                    try:
                        result = self.registry.execute(tool_name, tool_args)
                        observation = str(result)
                    except Exception as e:
                        observation = f"Error: {e}"
                        
                    # Yield Observation
                    yield AgentStep(
                        step_type=AgentStepType.OBSERVATION,
                        content=observation,
                        observation=observation
                    )
                    
                    # Add observation to history
                    current_history.append({
                        "role": "function", # or "tool"
                        "name": tool_name,
                        "content": observation
                    })
            
            except Exception as e:
                logger.error(f"Agent loop error: {e}", exc_info=True)
                yield AgentStep(
                    step_type=AgentStepType.ERROR,
                    content=f"An error occurred: {str(e)}"
                )
                break
