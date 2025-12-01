"""
Loop detection - pattern-based detection for tool call loops.
"""

from typing import List, Dict, Any, Tuple
import hashlib


class LoopDetector:
    """
    Detects loops in tool call sequences using pattern-based detection.
    
    Detects:
    - Exact repetition (A→A→A)
    - Alternating patterns (A→B→A→B)
    - Semantic loops (read→write→read)
    """
    
    def __init__(self, window_size: int = 5):
        """
        Initialize loop detector.
        
        Args:
            window_size: Number of recent actions to check for patterns
        """
        self.history: List[Tuple[str, ...]] = []
        self.window_size = window_size
    
    def _create_signature(self, tool_calls: List[Dict[str, Any]]) -> Tuple[str, ...]:
        """
        Create signature for tool calls.
        
        Args:
            tool_calls: List of tool call dictionaries
            
        Returns:
            Tuple signature for comparison
        """
        # Create signature from tool names and key inputs
        signature_parts = []
        for tc in sorted(tool_calls, key=lambda x: x.get("name", "")):
            tool_name = tc.get("name", "")
            tool_input = tc.get("input", {})
            
            # Include file path if present (important for detecting file loops)
            file_path = tool_input.get("file_path", "")
            if file_path:
                # Normalize path and take first 50 chars
                file_path = str(file_path).replace("\\", "/")[:50]
                signature_parts.append(f"{tool_name}:{file_path}")
            else:
                # Include other key inputs for non-file tools
                key_inputs = []
                for key in ["query", "pattern", "directory_path", "path"]:
                    if key in tool_input:
                        value = str(tool_input[key])[:30]
                        key_inputs.append(f"{key}={value}")
                if key_inputs:
                    signature_parts.append(f"{tool_name}:{':'.join(key_inputs)}")
                else:
                    signature_parts.append(tool_name)
        
        return tuple(signature_parts)
    
    def add_action(self, tool_calls: List[Dict[str, Any]]) -> bool:
        """
        Add tool call action and check for loops.
        
        Args:
            tool_calls: List of tool call dictionaries
            
        Returns:
            True if loop detected, False otherwise
        """
        signature = self._create_signature(tool_calls)
        self.history.append(signature)
        
        # Keep only recent history
        if len(self.history) > self.window_size * 2:
            self.history = self.history[-self.window_size * 2:]
        
        # Check for loops if we have enough history
        if len(self.history) >= self.window_size:
            return self._has_repetitive_pattern()
        
        return False
    
    def _has_repetitive_pattern(self) -> bool:
        """
        Check if recent history has repetitive patterns.
        
        Returns:
            True if repetitive pattern detected
        """
        recent = self.history[-self.window_size:]
        
        # Check for exact repetition (A→A→A)
        if len(recent) >= 3:
            if recent[-1] == recent[-2] == recent[-3]:
                return True
        
        # Check for alternating patterns (A→B→A→B)
        if len(recent) >= 4:
            # Check last 4 for A→B→A→B pattern
            if recent[-4] == recent[-2] and recent[-3] == recent[-1] and recent[-4] != recent[-3]:
                return True
        
        # Check for semantic loops (read→write→read pattern) with file path comparison
        if len(recent) >= 3:
            # Extract tool names and file paths
            tool_info = []
            for sig in recent[-3:]:
                if sig and len(sig) > 0:
                    # Split on ":" to get tool name and file path
                    parts = sig[0].split(":") if sig[0] else [""]
                    tool_name = parts[0] if parts else ""
                    file_path = parts[1] if len(parts) > 1 else ""
                    tool_info.append((tool_name, file_path))
                else:
                    tool_info.append(("", ""))
            
            # Check for read→write→read pattern on the SAME file
            if len(tool_info) >= 3:
                tool1, file1 = tool_info[-3]
                tool2, file2 = tool_info[-2]
                tool3, file3 = tool_info[-1]
                
                # Only flag as loop if same file is read→write→read
                if (tool1 == "read_file" and 
                    tool2 in ["write_file", "edit_file"] and 
                    tool3 == "read_file" and
                    file1 and file2 and file3 and
                    file1 == file2 == file3):  # Same file path
                    return True
        
        # Check for longer repetitive sequences
        if len(recent) >= 5:
            # Check if last 3 actions repeat
            pattern = recent[-3:]
            if len(self.history) >= 6:
                prev_pattern = self.history[-6:-3]
                if pattern == prev_pattern:
                    return True
        
        return False
    
    def reset(self):
        """Reset detection history."""
        self.history = []


