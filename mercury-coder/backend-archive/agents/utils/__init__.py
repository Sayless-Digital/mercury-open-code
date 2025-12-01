"""
Agent utility modules.
"""

import re
from typing import List

from .cache import LRUCacheWithTTL
from .path_utils import get_file_name, normalize_path


def extract_file_references(text: str) -> List[str]:
    """
    Extract file references from text using pattern matching.
    
    Args:
        text: Text to search for file references
        
    Returns:
        List of unique file paths found in text
    """
    file_refs = []
    
    # Look for common file patterns
    patterns = [
        r'([a-zA-Z0-9_/\\]+\.(py|js|ts|jsx|tsx|vue|java|cpp|h|json|yaml|yml|md|txt))',
        r'file[s]?\s+([a-zA-Z0-9_/\\]+\.(py|js|ts|jsx|tsx|vue|java|cpp|h))',
        r'in\s+([a-zA-Z0-9_/\\]+\.(py|js|ts|jsx|tsx|vue))',
        r'path[:\s]+([a-zA-Z0-9_/\\]+\.(py|js|ts|jsx|tsx|vue))',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            file_ref = match.group(1) if match.lastindex >= 1 else match.group(0)
            if file_ref and file_ref not in file_refs:
                file_refs.append(file_ref)
    
    return file_refs


__all__ = ['LRUCacheWithTTL', 'get_file_name', 'normalize_path', 'extract_file_references']

