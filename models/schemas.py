from typing import List, Optional
from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    request: str = Field(..., min_length=3, description="Natural language request")
    session_id: Optional[str] = Field(
        default="default", description="Used for conversation memory continuity"
    )


class PlanStep(BaseModel):
    id: int
    action: str
    description: str
    output_key: str


class ExecutionPlan(BaseModel):
    document_type: str
    title: str
    assumptions: List[str] = []
    steps: List[PlanStep]


class AgentResponse(BaseModel):
    message: str
    document_type: str
    title: str
    assumptions: List[str]
    task_list: List[PlanStep]
    document_path: str