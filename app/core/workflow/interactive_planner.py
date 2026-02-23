from typing import List, Dict, Any, Optional
import json
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class TaskPlanStep:
    step_id: int
    step_type: str  # "research", "outline", "content_gen", "image_gen", "review", "assembly"
    description: str
    input_data: Dict[str, Any] = field(default_factory=dict)
    expected_output: str = ""
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[Any] = None

@dataclass
class TaskPlan:
    task_id: str
    original_request: str
    steps: List[TaskPlanStep]
    context: Dict[str, Any] = field(default_factory=dict)
    status: str = "planning"

class InteractivePlanner:
    """
    Interactive Planner for complex tasks (like PPT generation).
    Breaks down a high-level request into verifiable steps.
    """
    
    @staticmethod
    def create_ppt_plan(user_input: str) -> TaskPlan:
        """
        Creates a structured plan for PPT generation.
        Phase 1: Research/Context (optional)
        Phase 2: Outline Design (Structure)
        Phase 3: Content Generation (Per Slide)
        Phase 4: Visuals Generation (Images)
        Phase 5: Assembly (PPTX build)
        """
        steps = []
        step_id = 1
        
        # Step 1: Research (if needed)
        steps.append(TaskPlanStep(
            step_id=step_id,
            step_type="research",
            description="Analyze user request and gather background context",
            input_data={"query": user_input},
            expected_output=" Context summary and key themes"
        ))
        step_id += 1

        # Step 2: Outline
        steps.append(TaskPlanStep(
            step_id=step_id,
            step_type="outline",
            description="Design PPT structure (Slides, Titles, Layouts)",
            input_data={"context_ref": 1},
            expected_output="JSON outline with slide titles and types"
        ))
        step_id += 1
        
        # Step 3: Detailed Content (Placeholder - will be expanded dynamically?)
        # For now, we add a "Content Planning" step that might spawn more sub-steps
        steps.append(TaskPlanStep(
            step_id=step_id,
            step_type="content_expansion",
            description="Generate detailed content for each slide",
            input_data={"outline_ref": 2},
            expected_output="Full markdown/JSON content for all slides"
        ))
        step_id += 1
        
        # Step 4: Assembly
        steps.append(TaskPlanStep(
            step_id=step_id,
            step_type="assembly",
            description="Compile content into final PPTX file",
            input_data={"content_ref": 3},
            expected_output="PPTX File path"
        ))

        return TaskPlan(
            task_id=f"ppt_{id(user_input)}",
            original_request=user_input,
            steps=steps
        )
