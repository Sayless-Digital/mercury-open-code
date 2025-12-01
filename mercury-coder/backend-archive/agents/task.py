"""
Task and Plan models for agent workflow.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger("mercury.agents.task")


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class WorkflowStage(Enum):
    """Workflow execution stages."""
    PLANNING = "planning"
    EXPLORING = "exploring"
    EXECUTING = "executing"
    VALIDATING = "validating"
    COMPLETED = "completed"
    ERROR = "error"


class Task:
    """Represents a single task in a plan."""
    
    def __init__(
        self,
        id: str,
        description: str,
        agent: str,
        dependencies: Optional[List[str]] = None,
        status: TaskStatus = TaskStatus.PENDING
    ):
        self.id = id
        self.description = description
        self.agent = agent
        self.dependencies = dependencies or []
        self.status = status
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """
        Create Task from dictionary.
        
        Uses TaskDataModel for validation - fails fast if validation fails.
        """
        # Use Pydantic validation as primary (fail fast on validation errors)
        from .models import TaskDataModel
        validated = TaskDataModel(**data)
        # Use validated data
        data = validated.dict()
        
        task = cls(
            id=data["id"],
            description=data["description"],
            agent=data["agent"],
            dependencies=data.get("dependencies", []),
            status=TaskStatus(data.get("status", "pending"))
        )
        task.result = data.get("result")
        if data.get("started_at"):
            task.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            task.completed_at = datetime.fromisoformat(data["completed_at"])
        task.error = data.get("error")
        return task
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary."""
        return {
            "id": self.id,
            "description": self.description,
            "agent": self.agent,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


class PlanBuilder:
    """
    Builder for Plan objects with early validation.
    
    Validates tasks and dependencies as they're added, before creating the Plan.
    """
    
    def __init__(self, plan_id: str, goal: str):
        """
        Initialize plan builder.
        
        Args:
            plan_id: Plan identifier
            goal: Plan goal
        """
        self.plan_id = plan_id
        self.goal = goal
        self.tasks: List[Task] = []
        self.task_ids: set = set()
    
    def add_task(self, task: Task) -> 'PlanBuilder':
        """
        Add a task to the plan with validation.
        
        Validates:
        - Task ID is unique
        - All dependency IDs exist
        - No circular dependencies
        
        Args:
            task: Task to add
            
        Returns:
            Self for method chaining
            
        Raises:
            ValueError: If validation fails
        """
        # Check for duplicate task ID
        if task.id in self.task_ids:
            raise ValueError(f"Task ID '{task.id}' already exists in plan")
        
        # Check that all dependencies exist
        for dep_id in task.dependencies:
            if dep_id not in self.task_ids:
                raise ValueError(f"Task '{task.id}' depends on non-existent task '{dep_id}'")
        
        # Check for circular dependency
        if self._would_create_circular_dependency(task):
            raise ValueError(f"Task '{task.id}' would create a circular dependency")
        
        # All validations passed, add the task
        self.tasks.append(task)
        self.task_ids.add(task.id)
        return self
    
    def _would_create_circular_dependency(self, new_task: Task) -> bool:
        """
        Check if adding this task would create a circular dependency.
        
        Args:
            new_task: Task to check
            
        Returns:
            True if circular dependency would be created
        """
        # Build task lookup including the new task
        all_tasks = self.tasks + [new_task]
        task_map = {t.id: t for t in all_tasks}
        
        # Use DFS to check for cycles
        visited = set()
        rec_stack = set()
        
        def dfs(current_id: str) -> bool:
            if current_id in rec_stack:
                return True  # Cycle detected
            if current_id in visited:
                return False
            
            visited.add(current_id)
            rec_stack.add(current_id)
            
            current_task = task_map.get(current_id)
            if current_task:
                for dep_id in current_task.dependencies:
                    if dfs(dep_id):
                        return True
            
            rec_stack.remove(current_id)
            return False
        
        return dfs(new_task.id)
    
    def build(self) -> 'Plan':
        """
        Build the Plan object.
        
        Returns:
            Validated Plan object
            
        Raises:
            ValueError: If plan is invalid (should not happen if using builder correctly)
        """
        # Final validation
        if not self.plan_id:
            raise ValueError("Plan ID cannot be empty")
        if not self.goal:
            raise ValueError("Plan goal cannot be empty")
        
        plan = Plan(id=self.plan_id, goal=self.goal, tasks=self.tasks)
        
        # Double-check validation (should pass if builder was used correctly)
        validation_errors = plan.validate_plan()
        if validation_errors:
            raise ValueError(f"Plan validation failed: {'; '.join(validation_errors)}")
        
        return plan


class Plan:
    """Represents a plan with multiple tasks."""
    
    def __init__(
        self,
        id: str,
        goal: str,
        tasks: Optional[List[Task]] = None
    ):
        self.id = id
        self.goal = goal
        self.tasks: List[Task] = tasks or []
        self.created_at = datetime.now()
        self.current_stage = WorkflowStage.PLANNING
    
    def add_task(self, task: Task):
        """
        Add a task to the plan with validation.
        
        Validates that:
        - Task ID is unique
        - All dependency IDs exist in the plan (or will exist)
        - No circular dependencies are introduced
        
        Args:
            task: Task to add
            
        Raises:
            ValueError: If validation fails
        """
        # Check for duplicate task ID
        existing_ids = {t.id for t in self.tasks}
        if task.id in existing_ids:
            raise ValueError(f"Task ID '{task.id}' already exists in plan")
        
        # Check that all dependencies exist (or will exist if we're building the plan)
        task_ids = existing_ids | {task.id}  # Include the new task
        for dep_id in task.dependencies:
            if dep_id not in task_ids:
                raise ValueError(f"Task '{task.id}' depends on non-existent task '{dep_id}'")
        
        # Check for circular dependency with this new task
        # Create temporary task list to check for cycles
        temp_tasks = self.tasks + [task]
        if self._has_circular_dependency_with_task(task, temp_tasks):
            raise ValueError(f"Task '{task.id}' would create a circular dependency")
        
        # All validations passed, add the task
        self.tasks.append(task)
    
    def _has_circular_dependency_with_task(self, task: Task, all_tasks: List[Task]) -> bool:
        """
        Check if adding this task would create a circular dependency.
        
        Args:
            task: Task to check
            all_tasks: All tasks including the new one
            
        Returns:
            True if circular dependency would be created
        """
        # Build task lookup
        task_map = {t.id: t for t in all_tasks}
        
        # Use DFS to check for cycles
        visited = set()
        rec_stack = set()
        
        def dfs(current_id: str) -> bool:
            if current_id in rec_stack:
                return True  # Cycle detected
            if current_id in visited:
                return False
            
            visited.add(current_id)
            rec_stack.add(current_id)
            
            current_task = task_map.get(current_id)
            if current_task:
                for dep_id in current_task.dependencies:
                    if dfs(dep_id):
                        return True
            
            rec_stack.remove(current_id)
            return False
        
        return dfs(task.id)
    
    def get_next_task(self) -> Optional[Task]:
        """Get the next pending task that has all dependencies met."""
        completed_ids = {t.id for t in self.tasks if t.status == TaskStatus.COMPLETED}
        
        for task in self.tasks:
            if task.status == TaskStatus.PENDING:
                # Check if all dependencies are completed
                if all(dep_id in completed_ids for dep_id in task.dependencies):
                    return task
        
        return None
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None
    
    def is_complete(self) -> bool:
        """Check if all tasks are completed."""
        return all(t.status == TaskStatus.COMPLETED for t in self.tasks)
    
    def has_failed_tasks(self) -> bool:
        """Check if any tasks have failed."""
        return any(t.status == TaskStatus.FAILED for t in self.tasks)
    
    def validate_plan(self) -> List[str]:
        """
        Validate plan for dependency errors.
        
        Checks:
        - All dependency IDs exist in task list
        - No circular dependencies
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        task_ids = {t.id for t in self.tasks}
        
        # Check that all dependency IDs exist
        for task in self.tasks:
            for dep_id in task.dependencies:
                if dep_id not in task_ids:
                    errors.append(f"Task '{task.id}' depends on non-existent task '{dep_id}'")
        
        # Check for circular dependencies using DFS
        for task in self.tasks:
            if self._has_circular_dependency(task, set(), set()):
                errors.append(f"Task '{task.id}' has circular dependency")
        
        return errors
    
    def _has_circular_dependency(
        self,
        task: Task,
        visited: set,
        rec_stack: set
    ) -> bool:
        """
        Check if task has circular dependency using DFS.
        
        Args:
            task: Task to check
            visited: Set of visited task IDs
            rec_stack: Set of tasks in current recursion stack
            
        Returns:
            True if circular dependency found
        """
        task_id = task.id
        
        # If already in recursion stack, we found a cycle
        if task_id in rec_stack:
            return True
        
        # If already visited (and not in stack), no cycle from here
        if task_id in visited:
            return False
        
        # Mark as visited and add to recursion stack
        visited.add(task_id)
        rec_stack.add(task_id)
        
        # Check all dependencies
        for dep_id in task.dependencies:
            dep_task = self.get_task(dep_id)
            if dep_task and self._has_circular_dependency(dep_task, visited, rec_stack):
                return True
        
        # Remove from recursion stack
        rec_stack.remove(task_id)
        return False
    
    def get_progress(self) -> Dict[str, Any]:
        """Get plan progress statistics."""
        total = len(self.tasks)
        completed = sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED)
        in_progress = sum(1 for t in self.tasks if t.status == TaskStatus.IN_PROGRESS)
        failed = sum(1 for t in self.tasks if t.status == TaskStatus.FAILED)
        pending = sum(1 for t in self.tasks if t.status == TaskStatus.PENDING)
        
        return {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "failed": failed,
            "pending": pending
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert plan to dictionary."""
        return {
            "id": self.id,
            "goal": self.goal,
            "tasks": [t.to_dict() for t in self.tasks],
            "created_at": self.created_at.isoformat(),
            "current_stage": self.current_stage.value,
            "progress": self.get_progress()
        }
