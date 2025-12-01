# Task Management System Design

## Overview
Comprehensive task management system enabling cancellation, pause, and resume of agent workflows with persistent state management.

## Architecture Components

### 1. TaskManager (Core)
**Purpose**: Central coordinator for task lifecycle management
**Responsibilities**:
- Manage multiple concurrent workflows
- Track task states and transitions
- Coordinate cancellation and pause/resume operations
- Maintain task registry and state consistency

**Key Methods**:
- `create_workflow(workflow_id, user_request, config)` - Initialize new workflow
- `cancel_workflow(workflow_id, reason)` - Cancel running workflow
- `pause_workflow(workflow_id, reason)` - Pause workflow at safe checkpoint
- `resume_workflow(workflow_id)` - Resume from last checkpoint
- `get_workflow_status(workflow_id)` - Query current state
- `cleanup_workflow(workflow_id)` - Clean up resources

### 2. CheckpointManager
**Purpose**: Handle state persistence and restoration
**Responsibilities**:
- Save workflow state at checkpoints
- Restore workflow from saved state
- Manage checkpoint storage (file-based + in-memory)
- Validate state consistency

**Checkpoint Data**:
```python
{
    "workflow_id": str,
    "checkpoint_id": str,
    "timestamp": datetime,
    "plan": dict,  # Plan.to_dict()
    "completed_tasks": list,
    "current_task_id": str,
    "task_results": dict,
    "workflow_stage": str,
    "agent_states": dict,
    "metadata": dict
}
```

**Key Methods**:
- `create_checkpoint(workflow_id, state_data)` - Save checkpoint
- `restore_checkpoint(workflow_id, checkpoint_id)` - Load checkpoint
- `list_checkpoints(workflow_id)` - Get all checkpoints
- `validate_checkpoint(checkpoint_data)` - Verify integrity
- `cleanup_old_checkpoints(days=7)` - Remove old data

### 3. ResourceManager
**Purpose**: Track and cleanup workflow resources
**Responsibilities**:
- Register cleanup handlers for tasks
- Execute cleanup on cancellation
- Track allocated resources (files, connections, etc.)
- Ensure proper resource disposal

**Key Methods**:
- `register_cleanup(workflow_id, task_id, handler)` - Add cleanup callback
- `cleanup_task(workflow_id, task_id)` - Execute task cleanup
- `cleanup_workflow(workflow_id)` - Execute all workflow cleanups
- `register_resource(workflow_id, resource)` - Track resource

### 4. StateTransitionManager
**Purpose**: Manage valid state transitions and logging
**Responsibilities**:
- Validate state transitions
- Log all state changes for audit
- Emit status events
- Track transition history

**Valid Transitions**:
```
PENDING → IN_PROGRESS
IN_PROGRESS → PAUSED
IN_PROGRESS → COMPLETED
IN_PROGRESS → FAILED
IN_PROGRESS → CANCELLED
PAUSED → IN_PROGRESS (resume)
PAUSED → CANCELLED
```

**Key Methods**:
- `transition(workflow_id, task_id, from_state, to_state, reason)` - Execute transition
- `validate_transition(from_state, to_state)` - Check validity
- `get_transition_history(workflow_id)` - Get audit log
- `emit_transition_event(workflow_id, event_data)` - Send to UI

### 5. CancellationManager
**Purpose**: Handle graceful cancellation
**Responsibilities**:
- Process cancellation requests
- Set cancellation flags
- Wait for safe cancellation points
- Handle concurrent cancellation requests
- Execute rollbacks if needed

**Key Methods**:
- `request_cancellation(workflow_id, reason, timeout)` - Initiate cancellation
- `is_cancelled(workflow_id)` - Check flag
- `mark_safe_point(workflow_id)` - Register checkpoint
- `wait_for_cancellation(workflow_id, timeout)` - Block until cancelled
- `rollback_if_needed(workflow_id, task_id)` - Undo partial work

### 6. ResumeQueue
**Purpose**: Manage resume requests with priority
**Responsibilities**:
- Queue paused workflows
- Prioritize resume requests
- Prevent concurrent resumes
- Manage resume order

**Priority Levels**:
- HIGH: User-initiated critical tasks
- NORMAL: Standard workflows
- LOW: Background tasks

**Key Methods**:
- `enqueue_resume(workflow_id, priority)` - Add to queue
- `dequeue_resume()` - Get next to resume
- `reprioritize(workflow_id, new_priority)` - Change priority
- `remove_from_queue(workflow_id)` - Cancel resume

### 7. TimeoutManager
**Purpose**: Handle task and workflow timeouts
**Responsibilities**:
- Set timeouts for tasks
- Monitor execution time
- Trigger cancellation on timeout
- Handle unresponsive tasks

**Key Methods**:
- `set_timeout(workflow_id, task_id, duration)` - Start timer
- `clear_timeout(workflow_id, task_id)` - Cancel timer
- `check_timeouts()` - Monitor all timeouts
- `handle_timeout(workflow_id, task_id)` - Process timeout event

### 8. AuditLogger
**Purpose**: Comprehensive logging and auditing
**Responsibilities**:
- Log all state transitions
- Track user actions
- Record errors and exceptions
- Provide audit trail for debugging

**Log Entry**:
```python
{
    "timestamp": datetime,
    "workflow_id": str,
    "task_id": str,
    "event_type": str,  # "state_change", "cancellation", "error", etc.
    "from_state": str,
    "to_state": str,
    "reason": str,
    "user_id": str,
    "metadata": dict
}
```

**Key Methods**:
- `log_event(workflow_id, event_type, data)` - Record event
- `log_state_change(workflow_id, task_id, transition)` - Log transition
- `log_error(workflow_id, error)` - Log exception
- `get_audit_trail(workflow_id)` - Retrieve logs
- `export_logs(workflow_id, format)` - Export for analysis

## Integration with Existing System

### OrchestratorAgent Integration
- `TaskManager` wraps orchestrator workflows
- Orchestrator methods delegate to TaskManager
- StatusEmitter integration for UI updates
- Backward compatibility maintained

### WorkflowManager Integration
- CheckpointManager saves state during execution
- ResourceManager tracks agent resources
- TimeoutManager monitors task execution
- Cancellation checks use CancellationManager

### Task Integration
- Task class extended with checkpoint data
- State transitions validated by StateTransitionManager
- Cleanup handlers registered with ResourceManager

## Data Persistence

### Storage Structure
```
backend/task_checkpoints/
├── {workflow_id}/
│   ├── checkpoints/
│   │   ├── checkpoint_001.json
│   │   ├── checkpoint_002.json
│   │   └── latest.json
│   ├── audit_log.jsonl
│   └── metadata.json
```

### Checkpoint File Format
```json
{
  "checkpoint_id": "cp_001",
  "timestamp": "2024-12-01T06:54:00Z",
  "workflow_id": "wf_123",
  "plan": {...},
  "completed_tasks": ["task1", "task2"],
  "current_task_id": "task3",
  "task_results": {...},
  "workflow_stage": "executing",
  "agent_states": {...},
  "resources": [...],
  "metadata": {...}
}
```

## Error Handling

### Edge Cases
1. **Concurrent Cancellation Requests**: Use locks to prevent race conditions
2. **Partially Completed Subtasks**: Checkpoint before each subtask
3. **Resource Leaks**: Always execute cleanup handlers
4. **State Corruption**: Validate checkpoints before restore
5. **Network Failures**: Retry with exponential backoff
6. **Unresponsive Tasks**: Timeout and force cancellation

### Rollback Strategy
1. Identify rollback points (checkpoints)
2. Execute registered rollback handlers
3. Restore state to last valid checkpoint
4. Clean up partial changes
5. Log rollback operation

## User Feedback

### Status Indicators
- Running: "⏳ Executing task 3/5..."
- Paused: "⏸️ Workflow paused at checkpoint 2"
- Cancelling: "🛑 Cancelling workflow, cleaning up..."
- Cancelled: "❌ Workflow cancelled"
- Completed: "✅ All tasks completed"
- Failed: "⚠️ Task 3 failed, attempting retry..."

### Confirmation Dialogs
- Cancel: "Cancel workflow? This will stop all running tasks."
- Pause: "Pause workflow? You can resume later from this point."
- Resume: "Resume workflow from last checkpoint?"
- Timeout: "Task taking too long. Cancel or wait?"

## Performance Considerations

### Optimization Strategies
1. **Checkpoint Frequency**: Balance between safety and performance
2. **Memory Management**: Stream large checkpoints to disk
3. **Lock Granularity**: Fine-grained locks to prevent bottlenecks
4. **Async Operations**: Non-blocking I/O for persistence
5. **Cache Management**: In-memory cache for recent checkpoints

### Scalability
- Support 100+ concurrent workflows
- Handle 1000+ checkpoints efficiently
- Process resume queue in <1s
- Cleanup old data automatically

## Testing Strategy

### Unit Tests
- Each component independently
- State transition validation
- Checkpoint save/restore
- Resource cleanup

### Integration Tests
- End-to-end workflow lifecycle
- Cancel during different stages
- Pause and resume
- Concurrent operations
- Timeout handling

### Stress Tests
- Multiple concurrent workflows
- Rapid cancel/resume cycles
- Large checkpoint data
- Resource exhaustion scenarios

## Security Considerations

### Access Control
- Validate user permissions for cancel/pause/resume
- Audit all user actions
- Prevent unauthorized checkpoint access

### Data Protection
- Encrypt sensitive checkpoint data
- Sanitize logs before export
- Secure storage permissions

## Monitoring and Metrics

### Key Metrics
- Active workflows count
- Average checkpoint creation time
- Resume success rate
- Cancellation response time
- Resource cleanup success rate
- Queue depth and wait time

### Alerts
- Failed checkpoint creation
- Timeout threshold exceeded
- Resource leak detected
- Queue depth too high
- State corruption detected