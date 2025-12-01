"""
Path utility functions for agents.
"""

from typing import Optional


def get_file_name(file_path: str) -> Optional[str]:
    """
    Extract just the filename from a path.
    
    Args:
        file_path: Full file path
        
    Returns:
        Filename or None if invalid
    """
    if not file_path or file_path == "...":
        return None
    # Handle both forward and backslash paths
    return file_path.replace("\\", "/").split("/")[-1]


def normalize_path(file_path: str) -> str:
    """
    Normalize file path (convert backslashes to forward slashes).
    
    Args:
        file_path: File path to normalize
        
    Returns:
        Normalized path
    """
    if not file_path:
        return ""
    return file_path.replace("\\", "/")

