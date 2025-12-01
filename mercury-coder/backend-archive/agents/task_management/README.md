# Task Management System

Comprehensive task lifecycle management for agent workflows with cancel, pause, and resume capabilities.

## Overview

The Task Management System provides enterprise-grade workflow control including:

- **Cancellation**: Graceful workflow cancellation with cleanup
- **Pause/Resume**: Save state and resume from checkpoints
- **State Persistence**: Automatic checkpoint creation and restoration
- **Resource Management**: Track and cleanup allocated resources
- **Timeout Handling**: Automatic timeout detection and handling
- **Priority Queue**: Priority-based resume queue system
- **Audit Logging**: Comprehensive event logging for debugging
- **UI Feedback**: User-friendly status messages and confirmations

## Architecture

```
TaskManager (Core Coordinator)
├── CheckpointManager (State Persistence)
├── StateTransitionManager (State Validation)
├── CancellationManager (Graceful Shutdown)
├── ResourceManager (Resource Cleanup)
├── TimeoutManager (Timeout Monitoring)
├── ResumeQueue (Priority Queue)
└── AuditLogger (Event Logging)
```

## Installation

The task management system is automatically installed with the agent framework. No additional setup required.

## Quick Start

### Basic Usage

```python
from backend.agents.task_management import TaskManager, ResumePriority

# Initialize task manager
task_manager = TaskManager(
    storage_dir="backend/task_checkpoints",
    default_task_timeout=300,  # 5 minutes
    default_workflow_timeout=3600  # 1 hour
)

# Create and start workflow
workflow_id = "my_workflow"
task_manager.create_workflow(
    workflow_id=workflow_id,
    user_request="Build a web application",
    config={"project_path": "/path/to/project"}
)

task_manager.start_workflow(workflow_id)

# Get status
status = task_manager.get_workflow_status(workflow_id)
print(status)
```

### Cancel Workflow

```python
# Cancel with reason
task_manager.cancel_workflow(
    workflow_id=workflow_id,
    reason="User requested cancellation",
    user_id="user123"
)

# Complete cancellation (cleanup resources)
await task_manager.complete_cancellation(workflow_id)
```

### Pause and Resume

```python
# Pause workflow (creates checkpoint)
task_manager.pause_workflow(
    workflow_id=workflow_id,
    reason="Need to modify requirements",
    user_id="user123"
)

# Resume with priority
await task_manager.resume_workflow(
    workflow_id=workflow_id,
    priority=ResumePriority.HIGH,
    user_id="user123"
)
```

### Resource Management

```python
# Register resource for tracking
task_manager.resource_manager.register_resource(
    workflow_id=workflow_id,
    resource_id="temp_file_1",
    resource_type="file",
    cleanup_handler=lambda: os.remove("/tmp/temp_file")
)

# Cleanup automatically handled on cancel/complete
```

### Timeout Handling

```python
# Set task timeout
task_manager.timeout_manager.set_task_timeout(
    workflow_id=workflow_id,
    task_id="task1",
    duration=300,  # 5 minutes
    callback=handle_timeout
)

# Check remaining time
remaining = task_manager.timeout_manager.get_remaining_time(
    workflow_id=workflow_id,
    task_id="task1"
)
```

## Integration with Orchestrator

### Using OrchestratorIntegration

```python
from backend.agents.task_management import TaskManager, OrchestratorIntegration
from backend.agents.orchestrator import OrchestratorAgent

# Create orchestrator
orchestrator = OrchestratorAgent(...)

# Wrap with task management
integration = OrchestratorIntegration(
    orchestrator=orchestrator,
    task_manager=TaskManager()
)

# Execute with full management
result = await integration.execute_workflow_with_management(
    user_request="Create a REST API",
    project_path="/path/to/project",
    session_id="session123"
)

# Cancel via integration
await integration.cancel_workflow(
    workflow_id=result["workflow_id"],
    reason="Requirements changed"
)
```

## UI Feedback

### Status Messages

```python
from backend.agents.task_management import UIFeedback

# Get user-friendly status
status = task_manager.get_workflow_status(workflow_id)
message = UIFeedback.get_status_message(status)
# Output: "⏳ Executing task 3/5..."

# Get comprehensive status
full_status = UIFeedback.format_comprehensive_status(status)
print(full_status)
```

### Confirmation Dialogs

```python
# Get confirmation dialog data for UI
dialog = UIFeedback.get_confirmation_dialog(
    action="cancel",
    workflow_id=workflow_id
)

# Returns:
{
    "title": "Cancel Workflow?",
    "message": "This will stop all running tasks...",
    "confirm_text": "Cancel Workflow",
    "cancel_text": "Keep Running",
    "variant": "danger"
}
```

### Notifications

```python
# Generate notification for events
notification = UIFeedback.get_notification(
    event_type="workflow_completed",
    workflow_id=workflow_id
)

# Returns:
{
    "title": "Workflow Completed",
    "message": "All tasks completed successfully",
    "type": "success",
    "timestamp": "2024-12-01T07:00:00Z"
}
```

## Checkpoints and State Persistence

### Manual Checkpoint

```python
# Create checkpoint manually
checkpoint_id = task_manager.checkpoint_manager.create_checkpoint(
    workflow_id=workflow_id,
    state_data={
        "plan": plan.to_dict(),
        "completed_tasks": ["task1", "task2"],
        "current_task_id": "task3"
    }
)

# Restore from specific checkpoint
state = task_manager.checkpoint_manager.restore_checkpoint(
    workflow_id=workflow_id,
    checkpoint_id=checkpoint_id
)
```

### List Checkpoints

```python
# Get all checkpoints
checkpoints = task_manager.checkpoint_manager.list_checkpoints(workflow_id)

for checkpoint in checkpoints:
    print(f"{checkpoint['checkpoint_id']} - {checkpoint['timestamp']}")
```

## Audit Logging

### Query Audit Trail

```python
# Get all events
audit_trail = task_manager.audit_logger.get_audit_trail(workflow_id)

# Filter by event type
cancellations = task_manager.audit_logger.get_audit_trail(
    workflow_id=workflow_id,
    event_type="cancellation"
)

# Get recent events only
recent = task_manager.audit_logger.get_audit_trail(
    workflow_id=workflow_id,
    limit=10
)
```

### Export Logs

```python
# Export to JSON
task_manager.audit_logger.export_logs(
    workflow_id=workflow_id,
    output_path="audit_log.json",
    format="json"
)

# Export to CSV
task_manager.audit_logger.export_logs(
    workflow_id=workflow_id,
    output_path="audit_log.csv",
    format="csv"
)
```

## Resume Queue

### Priority Management

```python
# Enqueue with high priority
task_manager.resume_queue.enqueue_resume(
    workflow_id=workflow_id,
    priority=ResumePriority.HIGH,
    requested_by="user123"
)

# Change priority
task_manager.resume_queue.reprioritize(
    workflow_id=workflow_id,
    new_priority=ResumePriority.NORMAL
)

# Get queue status
queue_status = task_manager.resume_queue.get_queue_status()
print(f"Queue size: {queue_status['queue_size']}")
print(f"In progress: {queue_status['in_progress']}")
```

### Process Queue

```python
async def resume_handler(workflow_id, metadata):
    """Handle resume operation."""
    return await task_manager.execute_resume(workflow_id)

# Process queue with handler
processed = await task_manager.resume_queue.process_queue(
    resume_handler=resume_handler,
    max_iterations=10
)
```

## Advanced Features

### Rollback Handlers

```python
# Register rollback for a task
def rollback_task():
    # Undo changes made by task
    database.rollback_transaction()
    filesystem.remove_temp_files()

task_manager.cancellation_manager.register_rollback_handler(
    workflow_id=workflow_id,
    task_id="task1",
    handler=rollback_task
)

# Execute rollback on cancellation
await task_manager.cancellation_manager.execute_rollback(
    workflow_id=workflow_id,
    task_id="task1"
)
```

### State Transitions

```python
from backend.agents.task import TaskStatus

# Validate transition
valid = task_manager.state_transition_manager.validate_task_transition(
    from_state=TaskStatus.IN_PROGRESS,
    to_state=TaskStatus.PAUSED
)

# Execute transition with logging
task_manager.state_transition_manager.transition_task(
    workflow_id=workflow_id,
    task_id="task1",
    from_state=TaskStatus.IN_PROGRESS,
    to_state=TaskStatus.COMPLETED,
    reason="Task completed successfully"
)
```

### Concurrent Workflow Management

```python
# Manage multiple workflows
workflow_ids = []
for i in range(10):
    wf_id = f"workflow_{i}"
    task_manager.create_workflow(wf_id, f"Request {i}")
    task_manager.start_workflow(wf_id)
    workflow_ids.append(wf_id)

# Get all workflow statuses
all_workflows = task_manager.get_all_workflows()

# Cancel specific workflows
for wf_id in workflow_ids[:5]:
    task_manager.cancel_workflow(wf_id)

# Pause others
for wf_id in workflow_ids[5:]:
    task_manager.pause_workflow(wf_id)
```

## Error Handling

### Edge Cases Handled

1. **Concurrent Cancellation Requests**: Thread-safe locks prevent race conditions
2. **Partially Completed Subtasks**: Checkpoints created before each subtask
3. **Resource Leaks**: All resources tracked and cleaned up
4. **State Corruption**: Checkpoint validation before restore
5. **Unresponsive Tasks**: Automatic timeout and force cancellation
6. **Network Failures**: Retry logic with exponential backoff

### Example Error Handling

```python
try:
    await task_manager.resume_workflow(workflow_id)
except Exception as e:
    logger.error(f"Resume failed: {e}")
    
    # Check if checkpoint is corrupted
    checkpoints = task_manager.checkpoint_manager.list_checkpoints(workflow_id)
    if not checkpoints:
        logger.error("No valid checkpoints found")
        # Handle recovery
```

## Performance Considerations

- **Checkpoint Frequency**: Balance safety vs performance (default: after each task)
- **Memory Management**: Checkpoints are streamed to disk for large workflows
- **Lock Granularity**: Fine-grained locks prevent bottlenecks
- **Async Operations**: All I/O operations are non-blocking
- **Cache Management**: In-memory cache for recent checkpoints

## Configuration

### Environment Variables

```bash
# Checkpoint storage directory
TASK_CHECKPOINT_DIR=backend/task_checkpoints

# Default timeouts
TASK_TIMEOUT_SECONDS=300
WORKFLOW_TIMEOUT_SECONDS=3600

# Queue settings
MAX_CONCURRENT_RESUMES=3
MAX_CHECKPOINTS_PER_WORKFLOW=10
```

### Custom Configuration

```python
task_manager = TaskManager(
    storage_dir="custom/path",
    default_task_timeout=600,  # 10 minutes
    default_workflow_timeout=7200,  # 2 hours
    max_checkpoints=20,
    max_concurrent_resumes=5
)
```

## Testing

Run tests:

```bash
# Run all tests
pytest backend/agents/task_management/tests/

# Run specific test file
pytest backend/agents/task_management/tests/test_task_manager.py

# Run with coverage
pytest backend/agents/task_management/tests/ --cov=backend/agents/task_management
```

## Troubleshooting

### Common Issues

1. **Checkpoint Restoration Fails**
   - Check checkpoint file permissions
   - Verify checkpoint data integrity
   - Ensure sufficient disk space

2. **Timeout Not Working**
   - Verify monitoring task is running
   - Check timeout duration configuration
   - Review callback function

3. **Resume Queue Stuck**
   - Check max_concurrent_resumes limit
   - Verify resume handler is working
   - Review queue status

### Debug Logging

Enable debug logging:

```python
import logging

logging.getLogger("mercury.agents.task_management").setLevel(logging.DEBUG)
```

## API Reference

See individual module documentation:

- [`TaskManager`](./task_manager.py) - Core coordinator
- [`CheckpointManager`](./checkpoint_manager.py) - State persistence
- [`CancellationManager`](./cancellation_manager.py) - Cancellation handling
- [`ResourceManager`](./resource_manager.py) - Resource tracking
- [`TimeoutManager`](./timeout_manager.py) - Timeout monitoring
- [`ResumeQueue`](./resume_queue.py) - Priority queue
- [`AuditLogger`](./audit_logger.py) - Event logging
- [`UIFeedback`](./ui_feedback.py) - User interface helpers

## Contributing

When adding new features:

1. Add tests to `tests/` directory
2. Update this README with usage examples
3. Add docstrings to all public methods
4. Update DESIGN.md if architecture changes

## License

Part of the Mercury Coder project.