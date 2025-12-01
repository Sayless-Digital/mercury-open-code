"""
Tests for TaskManager and integrated components.
"""

import pytest
import asyncio
from datetime import datetime
from pathlib import Path
import tempfile
import shutil

from ..task_manager import TaskManager, WorkflowState
from ..resume_queue import ResumePriority
from ...task import Plan, Task, TaskStatus


class TestTaskManager:
    """Test TaskManager functionality."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def task_manager(self, temp_dir):
        """Create TaskManager instance."""
        return TaskManager(
            storage_dir=temp_dir,
            default_task_timeout=10,
            default_workflow_timeout=60,
            max_checkpoints=5,
            max_concurrent_resumes=2
        )
    
    def test_create_workflow(self, task_manager):
        """Test workflow creation."""
        workflow_id = "test_workflow_1"
        success = task_manager.create_workflow(
            workflow_id=workflow_id,
            user_request="Test request",
            config={"test": "config"}
        )
        
        assert success
        assert workflow_id in task_manager._workflows
        assert task_manager._workflow_states[workflow_id] == WorkflowState.CREATED
    
    def test_create_duplicate_workflow(self, task_manager):
        """Test creating duplicate workflow fails."""
        workflow_id = "test_workflow_1"
        task_manager.create_workflow(workflow_id, "Test request")
        
        # Should fail on duplicate
        success = task_manager.create_workflow(workflow_id, "Test request 2")
        assert not success
    
    def test_start_workflow(self, task_manager):
        """Test workflow start."""
        workflow_id = "test_workflow_1"
        task_manager.create_workflow(workflow_id, "Test request")
        
        # Create a simple plan
        plan = Plan(id="plan1", goal="Test goal")
        
        success = task_manager.start_workflow(workflow_id, plan)
        assert success
        assert task_manager._workflow_states[workflow_id] == WorkflowState.RUNNING
        assert task_manager._workflow_plans[workflow_id] == plan
    
    def test_cancel_workflow(self, task_manager):
        """Test workflow cancellation."""
        workflow_id = "test_workflow_1"
        task_manager.create_workflow(workflow_id, "Test request")
        task_manager.start_workflow(workflow_id)
        
        success = task_manager.cancel_workflow(
            workflow_id=workflow_id,
            reason="Test cancellation",
            user_id="test_user"
        )
        
        assert success
        assert task_manager._workflow_states[workflow_id] == WorkflowState.CANCELLING
        assert task_manager.cancellation_manager.is_cancelled(workflow_id)
    
    @pytest.mark.asyncio
    async def test_complete_cancellation(self, task_manager):
        """Test cancellation completion."""
        workflow_id = "test_workflow_1"
        task_manager.create_workflow(workflow_id, "Test request")
        task_manager.start_workflow(workflow_id)
        task_manager.cancel_workflow(workflow_id)
        
        success = await task_manager.complete_cancellation(workflow_id)
        assert success
        assert task_manager._workflow_states[workflow_id] == WorkflowState.CANCELLED
    
    def test_pause_workflow(self, task_manager):
        """Test workflow pause."""
        workflow_id = "test_workflow_1"
        task_manager.create_workflow(workflow_id, "Test request")
        
        # Create plan with tasks
        plan = Plan(id="plan1", goal="Test goal")
        task1 = Task(id="task1", description="Task 1", agent="coder")
        plan.add_task(task1)
        
        task_manager.start_workflow(workflow_id, plan)
        
        success = task_manager.pause_workflow(
            workflow_id=workflow_id,
            reason="Test pause",
            user_id="test_user"
        )
        
        assert success
        assert task_manager._workflow_states[workflow_id] == WorkflowState.PAUSED
        
        # Should have created a checkpoint
        checkpoints = task_manager.checkpoint_manager.list_checkpoints(workflow_id)
        assert len(checkpoints) > 0
    
    @pytest.mark.asyncio
    async def test_resume_workflow(self, task_manager):
        """Test workflow resume."""
        workflow_id = "test_workflow_1"
        task_manager.create_workflow(workflow_id, "Test request")
        
        plan = Plan(id="plan1", goal="Test goal")
        task_manager.start_workflow(workflow_id, plan)
        task_manager.pause_workflow(workflow_id)
        
        # Resume with normal priority
        success = await task_manager.resume_workflow(
            workflow_id=workflow_id,
            priority=ResumePriority.NORMAL,
            user_id="test_user"
        )
        
        assert success
        assert task_manager._workflow_states[workflow_id] == WorkflowState.RUNNING
    
    def test_complete_workflow(self, task_manager):
        """Test workflow completion."""
        workflow_id = "test_workflow_1"
        task_manager.create_workflow(workflow_id, "Test request")
        task_manager.start_workflow(workflow_id)
        
        success = task_manager.complete_workflow(
            workflow_id=workflow_id,
            success=True
        )
        
        assert success
        assert task_manager._workflow_states[workflow_id] == WorkflowState.COMPLETED
    
    def test_get_workflow_status(self, task_manager):
        """Test getting workflow status."""
        workflow_id = "test_workflow_1"
        task_manager.create_workflow(workflow_id, "Test request")
        
        status = task_manager.get_workflow_status(workflow_id)
        
        assert status["workflow_id"] == workflow_id
        assert status["state"] == WorkflowState.CREATED.value
        assert "created_at" in status
        assert "user_request" in status
    
    @pytest.mark.asyncio
    async def test_cleanup_workflow(self, task_manager):
        """Test workflow cleanup."""
        workflow_id = "test_workflow_1"
        task_manager.create_workflow(workflow_id, "Test request")
        task_manager.start_workflow(workflow_id)
        
        success = await task_manager.cleanup_workflow(workflow_id)
        assert success
        assert workflow_id not in task_manager._workflows
        assert workflow_id not in task_manager._workflow_states
    
    def test_get_all_workflows(self, task_manager):
        """Test getting all workflows."""
        # Create multiple workflows
        for i in range(3):
            workflow_id = f"test_workflow_{i}"
            task_manager.create_workflow(workflow_id, f"Test request {i}")
        
        workflows = task_manager.get_all_workflows()
        assert len(workflows) == 3
        assert all(isinstance(w, dict) for w in workflows)
    
    @pytest.mark.asyncio
    async def test_concurrent_workflows(self, task_manager):
        """Test managing multiple concurrent workflows."""
        workflow_ids = [f"workflow_{i}" for i in range(5)]
        
        # Create all workflows
        for wf_id in workflow_ids:
            task_manager.create_workflow(wf_id, f"Request for {wf_id}")
            task_manager.start_workflow(wf_id)
        
        # All should be running
        for wf_id in workflow_ids:
            status = task_manager.get_workflow_status(wf_id)
            assert status["state"] == WorkflowState.RUNNING.value
        
        # Cancel some, pause others
        task_manager.cancel_workflow(workflow_ids[0])
        task_manager.pause_workflow(workflow_ids[1])
        task_manager.complete_workflow(workflow_ids[2], success=True)
        
        # Verify states
        assert task_manager._workflow_states[workflow_ids[0]] == WorkflowState.CANCELLING
        assert task_manager._workflow_states[workflow_ids[1]] == WorkflowState.PAUSED
        assert task_manager._workflow_states[workflow_ids[2]] == WorkflowState.COMPLETED
        assert task_manager._workflow_states[workflow_ids[3]] == WorkflowState.RUNNING


class TestCheckpointManager:
    """Test CheckpointManager functionality."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def checkpoint_manager(self, temp_dir):
        """Create CheckpointManager instance."""
        from ..checkpoint_manager import CheckpointManager
        return CheckpointManager(storage_dir=temp_dir, max_checkpoints=3)
    
    def test_create_checkpoint(self, checkpoint_manager):
        """Test checkpoint creation."""
        workflow_id = "test_workflow"
        state_data = {
            "plan": {"tasks": []},
            "completed_tasks": ["task1"],
            "current_task_id": "task2"
        }
        
        checkpoint_id = checkpoint_manager.create_checkpoint(workflow_id, state_data)
        assert checkpoint_id is not None
        assert checkpoint_id.startswith("cp_")
    
    def test_restore_checkpoint(self, checkpoint_manager):
        """Test checkpoint restoration."""
        workflow_id = "test_workflow"
        state_data = {
            "plan": {"tasks": ["task1", "task2"]},
            "completed_tasks": ["task1"]
        }
        
        checkpoint_id = checkpoint_manager.create_checkpoint(workflow_id, state_data)
        restored_data = checkpoint_manager.restore_checkpoint(workflow_id, checkpoint_id)
        
        assert restored_data is not None
        assert restored_data["plan"] == state_data["plan"]
        assert restored_data["completed_tasks"] == state_data["completed_tasks"]
    
    def test_list_checkpoints(self, checkpoint_manager):
        """Test listing checkpoints."""
        workflow_id = "test_workflow"
        
        # Create multiple checkpoints
        for i in range(3):
            checkpoint_manager.create_checkpoint(
                workflow_id,
                {"data": f"checkpoint_{i}"}
            )
        
        checkpoints = checkpoint_manager.list_checkpoints(workflow_id)
        assert len(checkpoints) == 3
        assert all("checkpoint_id" in cp for cp in checkpoints)
    
    def test_max_checkpoints_cleanup(self, checkpoint_manager):
        """Test automatic cleanup of old checkpoints."""
        workflow_id = "test_workflow"
        
        # Create more than max_checkpoints
        for i in range(5):
            checkpoint_manager.create_checkpoint(
                workflow_id,
                {"data": f"checkpoint_{i}"}
            )
        
        checkpoints = checkpoint_manager.list_checkpoints(workflow_id)
        assert len(checkpoints) <= 3  # max_checkpoints


class TestCancellationManager:
    """Test CancellationManager functionality."""
    
    @pytest.fixture
    def cancellation_manager(self):
        """Create CancellationManager instance."""
        from ..cancellation_manager import CancellationManager
        return CancellationManager(default_timeout=5)
    
    def test_request_cancellation(self, cancellation_manager):
        """Test cancellation request."""
        workflow_id = "test_workflow"
        
        success = cancellation_manager.request_cancellation(
            workflow_id=workflow_id,
            reason="Test cancellation"
        )
        
        assert success
        assert cancellation_manager.is_cancelled(workflow_id)
        assert cancellation_manager.get_cancellation_reason(workflow_id) == "Test cancellation"
    
    def test_mark_safe_point(self, cancellation_manager):
        """Test marking safe cancellation points."""
        workflow_id = "test_workflow"
        
        cancellation_manager.mark_safe_point(workflow_id, "checkpoint1")
        cancellation_manager.mark_safe_point(workflow_id, "checkpoint2")
        
        # Should have 2 safe points
        assert len(cancellation_manager._safe_points.get(workflow_id, set())) == 2
    
    @pytest.mark.asyncio
    async def test_register_rollback_handler(self, cancellation_manager):
        """Test rollback handler registration."""
        workflow_id = "test_workflow"
        task_id = "task1"
        
        rollback_called = []
        
        def rollback_handler():
            rollback_called.append(True)
        
        cancellation_manager.register_rollback_handler(
            workflow_id, task_id, rollback_handler
        )
        
        await cancellation_manager.execute_rollback(workflow_id, task_id)
        
        assert len(rollback_called) == 1


class TestResumeQueue:
    """Test ResumeQueue functionality."""
    
    @pytest.fixture
    def resume_queue(self):
        """Create ResumeQueue instance."""
        from ..resume_queue import ResumeQueue
        return ResumeQueue(max_concurrent_resumes=2)
    
    def test_enqueue_resume(self, resume_queue):
        """Test enqueueing resume requests."""
        success = resume_queue.enqueue_resume(
            workflow_id="workflow1",
            priority=ResumePriority.NORMAL
        )
        
        assert success
        assert resume_queue.get_queue_status()["queue_size"] == 1
    
    def test_dequeue_resume(self, resume_queue):
        """Test dequeueing resume requests."""
        resume_queue.enqueue_resume("workflow1", ResumePriority.NORMAL)
        
        request = resume_queue.dequeue_resume()
        
        assert request is not None
        assert request.workflow_id == "workflow1"
        assert resume_queue.is_in_progress("workflow1")
    
    def test_priority_ordering(self, resume_queue):
        """Test priority-based ordering."""
        # Add requests with different priorities
        resume_queue.enqueue_resume("workflow1", ResumePriority.LOW)
        resume_queue.enqueue_resume("workflow2", ResumePriority.HIGH)
        resume_queue.enqueue_resume("workflow3", ResumePriority.NORMAL)
        
        # Dequeue should return high priority first
        request = resume_queue.dequeue_resume()
        assert request.workflow_id == "workflow2"
    
    def test_complete_resume(self, resume_queue):
        """Test completing resume operation."""
        resume_queue.enqueue_resume("workflow1", ResumePriority.NORMAL)
        request = resume_queue.dequeue_resume()
        
        resume_queue.complete_resume("workflow1", success=True)
        
        assert not resume_queue.is_in_progress("workflow1")
        assert resume_queue.is_completed("workflow1")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])