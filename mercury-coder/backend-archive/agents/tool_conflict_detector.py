"""
Tool conflict detection - dynamic grouping of tools based on actual conflicts.
"""

import logging
from typing import List, Dict, Any, Tuple, Set, Optional
import os

logger = logging.getLogger("mercury.agents.tool_conflict_detector")


def tools_conflict(tool1: Dict[str, Any], tool2: Dict[str, Any]) -> bool:
    """
    Check if two tools conflict with each other.
    
    Args:
        tool1: First tool call dictionary
        tool2: Second tool call dictionary
        
    Returns:
        True if tools conflict, False otherwise
    """
    name1 = tool1.get("name", "")
    name2 = tool2.get("name", "")
    input1 = tool1.get("input", {})
    input2 = tool2.get("input", {})
    
    # Get file paths
    file1 = input1.get("file_path") or input1.get("path") or ""
    file2 = input2.get("file_path") or input2.get("path") or ""
    
    # Normalize paths
    if file1:
        file1 = os.path.normpath(str(file1))
    if file2:
        file2 = os.path.normpath(str(file2))
    
    # Same file operations always conflict
    if file1 and file2 and file1 == file2:
        return True
    
    # Write operations on same file conflict
    write_ops = {"write_file", "edit_file", "delete_file", "move_file", "copy_file"}
    if name1 in write_ops and name2 in write_ops:
        if file1 and file2 and file1 == file2:
            return True
    
    # Read + write on same file conflict (read might be stale)
    read_ops = {"read_file", "read_json_file", "read_yaml_file", "read_env_file"}
    if (name1 in write_ops and name2 in read_ops) or (name1 in read_ops and name2 in write_ops):
        if file1 and file2 and file1 == file2:
            return True
    
    # Directory operations conflict if same directory
    dir1 = input1.get("directory_path") or ""
    dir2 = input2.get("directory_path") or ""
    if dir1 and dir2:
        dir1 = os.path.normpath(str(dir1))
        dir2 = os.path.normpath(str(dir2))
        if dir1 == dir2:
            # Directory write operations conflict
            dir_write_ops = {"create_directory", "delete_directory", "move_file", "copy_file"}
            if name1 in dir_write_ops or name2 in dir_write_ops:
                return True
    
    return False


def is_write_operation(tool: Dict[str, Any]) -> bool:
    """
    Check if tool is a write operation.
    
    Args:
        tool: Tool call dictionary
        
    Returns:
        True if write operation
    """
    write_ops = {
        "write_file", "edit_file", "search_replace_in_multiple_files",
        "write_json_file", "write_yaml_file", "write_env_file",
        "delete_file", "delete_directory", "create_directory",
        "move_file", "copy_file", "git_add", "git_commit"
    }
    return tool.get("name", "") in write_ops


def group_tools_by_conflicts(
    tool_calls: List[Dict[str, Any]],
    file_graph: Optional[Any] = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Group tools into parallel and sequential based on actual conflicts.
    
    Args:
        tool_calls: List of tool call dictionaries
        file_graph: Optional file graph for detecting related file conflicts
        
    Returns:
        Tuple of (parallel_tools, sequential_tools)
    """
    parallel = []
    sequential = []
    conflict_count = 0
    
    for i, tool in enumerate(tool_calls):
        tool_name = tool.get("name", "unknown")
        # Check if this tool conflicts with any previous tool
        has_conflict = False
        conflict_reason = None
        
        # Check against all previous tools
        for prev_tool in tool_calls[:i]:
            if tools_conflict(tool, prev_tool):
                has_conflict = True
                conflict_reason = f"Direct conflict with {prev_tool.get('name', 'unknown')}"
                conflict_count += 1
                break
            
            # Check file graph for related file conflicts if available
            if file_graph:
                file1 = tool.get("input", {}).get("file_path") or ""
                file2 = prev_tool.get("input", {}).get("file_path") or ""
                
                if file1 and file2 and file1 != file2:
                    # Check if files are related (one imports the other)
                    try:
                        deps1 = file_graph.get_file_dependencies(file1)
                        deps2 = file_graph.get_file_dependencies(file2)
                        
                        # If one file depends on the other and we're writing to it
                        if is_write_operation(tool) or is_write_operation(prev_tool):
                            if file2 in (deps1.get("dependencies", []) or []):
                                has_conflict = True
                                conflict_reason = f"Dependency conflict: {file1} depends on {file2}"
                                conflict_count += 1
                                break
                            if file1 in (deps2.get("dependencies", []) or []):
                                has_conflict = True
                                conflict_reason = f"Dependency conflict: {file2} depends on {file1}"
                                conflict_count += 1
                                break
                    except Exception as e:
                        # Log file graph lookup failures instead of silently ignoring
                        logger.debug(f"File graph lookup failed for conflict detection: {e}")
                        # If file graph lookup fails, be conservative
                        pass
        
        # Write operations are generally sequential unless proven safe
        if has_conflict or is_write_operation(tool):
            sequential.append(tool)
            if has_conflict and conflict_reason:
                logger.debug(f"Tool {tool_name} marked sequential: {conflict_reason}")
        else:
            parallel.append(tool)
    
    if conflict_count > 0:
        logger.info(f"Detected {conflict_count} tool conflicts, {len(sequential)} tools will run sequentially")
    
    return parallel, sequential


