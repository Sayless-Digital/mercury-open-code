"""
Pydantic models for agent task inputs and validation.
"""

from typing import Dict, List, Any, Optional, TypedDict
from pydantic import BaseModel, Field, validator
from datetime import datetime


class AgentResponse(TypedDict, total=False):
    """
    Standardized response format for all agent execute() methods.
    
    All agents should return this format for consistency.
    """
    success: bool  # Required
    result: Dict[str, Any]  # Required - agent-specific result data
    message: str  # Required - human-readable message
    next_action: Optional[str]  # Optional - suggested next action


class TaskInput(BaseModel):
    """Validated task input model."""
    
    description: str = Field(..., min_length=1, description="Task description")
    goal: Optional[str] = Field(None, description="Overall goal this task contributes to")
    project_path: Optional[str] = Field(None, description="Project root path")
    task_id: Optional[str] = Field(None, description="Unique task identifier")
    retry_count: int = Field(0, ge=0, description="Number of retry attempts")
    exploration_findings: Optional[Dict[str, Any]] = Field(None, description="Findings from exploration phase")
    previous_recommendations: Optional[str] = Field(None, description="Previous recommendations")
    files_changed: Optional[List[str]] = Field(None, description="List of modified files")
    conversational: bool = Field(False, description="Whether this is a conversational task")
    
    @validator('description')
    def description_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Task description cannot be empty')
        return v.strip()
    
    class Config:
        extra = "allow"  # Allow additional fields for flexibility


class AgentContextModel(BaseModel):
    """Validated agent context model."""
    
    session_id: Optional[str] = Field(None, description="Session identifier")
    project_path: Optional[str] = Field(None, description="Project root path")
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list, description="Conversation history")
    recent_messages: List[Dict[str, Any]] = Field(default_factory=list, description="Recent messages")
    completed_tasks: List[str] = Field(default_factory=list, description="Completed task IDs")
    plan_goal: Optional[str] = Field(None, description="Overall plan goal")
    research_findings: Optional[str] = Field(None, description="Research findings")
    exploration_findings: Optional[str] = Field(None, description="Exploration findings")
    proactive_cache: Optional[Dict[str, str]] = Field(None, description="Proactive search cache")
    task_results: Optional[Dict[str, Any]] = Field(None, description="Results from previous tasks")
    files_changed: Optional[List[str]] = Field(None, description="List of modified files")
    
    class Config:
        extra = "allow"  # Allow additional fields for flexibility


class PlanDataModel(BaseModel):
    """Validated plan data model."""
    
    plan_id: str = Field(..., min_length=1, description="Plan identifier")
    goal: str = Field(..., min_length=1, description="Plan goal")
    tasks: List[Dict[str, Any]] = Field(default_factory=list, description="List of task dictionaries")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    current_stage: Optional[str] = Field(None, description="Current workflow stage")
    
    @validator('plan_id')
    def plan_id_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Plan ID cannot be empty')
        return v.strip()
    
    @validator('goal')
    def goal_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Plan goal cannot be empty')
        return v.strip()
    
    @validator('tasks')
    def validate_tasks(cls, v):
        if not isinstance(v, list):
            raise ValueError('Tasks must be a list')
        # Validate each task has required fields
        for i, task in enumerate(v):
            if not isinstance(task, dict):
                raise ValueError(f'Task {i} must be a dictionary')
            if 'description' not in task:
                raise ValueError(f'Task {i} missing required field: description')
            if 'agent' not in task:
                raise ValueError(f'Task {i} missing required field: agent')
        return v
    
    class Config:
        extra = "allow"


class TaskDataModel(BaseModel):
    """Validated task data model."""
    
    id: str = Field(..., min_length=1, description="Task identifier")
    description: str = Field(..., min_length=1, description="Task description")
    agent: str = Field(..., min_length=1, description="Agent name to execute task")
    dependencies: List[str] = Field(default_factory=list, description="Task dependencies")
    status: Optional[str] = Field(None, description="Task status")
    
    @validator('id')
    def id_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Task ID cannot be empty')
        return v.strip()
    
    @validator('description')
    def description_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Task description cannot be empty')
        return v.strip()
    
    @validator('agent')
    def agent_valid(cls, v):
        valid_agents = ['researcher', 'planner', 'coder', 'analyzer']
        if v not in valid_agents:
            raise ValueError(f'Invalid agent: {v}. Must be one of {valid_agents}')
        return v
    
    class Config:
        extra = "allow"

