from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from enum import Enum

class AgentStepType(Enum):
    THOUGHT = "thought"
    ACTION = "action"
    OBSERVATION = "observation"
    ANSWER = "answer"
    ERROR = "error"

@dataclass
class AgentAction:
    tool_name: str
    tool_args: Dict[str, Any]
    tool_call_id: Optional[str] = None

@dataclass
class AgentStep:
    step_type: AgentStepType
    content: str
    action: Optional[AgentAction] = None
    observation: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "step_type": self.step_type.value,
            "content": self.content,
            "metadata": self.metadata
        }
        if self.action:
            result["action"] = {
                "tool_name": self.action.tool_name,
                "tool_args": self.action.tool_args,
                "tool_call_id": self.action.tool_call_id
            }
        if self.observation:
            result["observation"] = self.observation
        return result

@dataclass
class AgentResponse:
    content: str
    steps: List[AgentStep]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "steps": [step.to_dict() for step in self.steps],
            "metadata": self.metadata
        }
