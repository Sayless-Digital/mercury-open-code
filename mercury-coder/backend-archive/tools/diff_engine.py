"""
Diff Engine - Computes unified diffs and minimal patches.
Implements diff-first approach for top-tier AI agent behavior.
"""

import difflib
import re
import logging
from typing import Dict, List, Tuple, Optional, Any

logger = logging.getLogger("mercury.tools.diff_engine")


class DiffEngine:
    """
    Computes unified diffs and minimal patches between file versions.
    
    Features:
    - Unified diff format
    - Minimal patches (only changed lines)
    - Conflict detection
    - Multi-file diff operations
    - Diff statistics
    """
    
    def __init__(self):
        """Initialize diff engine."""
        pass
    
    def compute_unified_diff(
        self,
        old_content: str,
        new_content: str,
        file_path: str = "file",
        context_lines: int = 3
    ) -> str:
        """
        Compute unified diff between old and new content.
        
        Args:
            old_content: Original file content
            new_content: New file content
            file_path: Path to file (for diff header)
            context_lines: Number of context lines to include
            
        Returns:
            Unified diff string
        """
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        
        # Generate unified diff
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=file_path,
            tofile=file_path,
            lineterm='',
            n=context_lines
        )
        
        return ''.join(diff)
    
    def compute_minimal_patch(
        self,
        old_content: str,
        new_content: str,
        file_path: str = "file"
    ) -> Dict[str, Any]:
        """
        Compute minimal patch (only changed lines).
        
        Args:
            old_content: Original file content
            new_content: New file content
            file_path: Path to file
            
        Returns:
            Dict with:
            - patch: Minimal patch string
            - changes: List of change operations
            - stats: Diff statistics
        """
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        
        # Use SequenceMatcher to find minimal changes
        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        
        changes = []
        current_old_start = 0
        current_new_start = 0
        
        for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
            if tag == 'replace':
                # Lines replaced
                old_block = old_lines[old_start:old_end]
                new_block = new_lines[new_start:new_end]
                changes.append({
                    "type": "replace",
                    "old_start": old_start + 1,  # 1-indexed
                    "old_end": old_end,
                    "new_start": new_start + 1,
                    "new_end": new_end,
                    "old_lines": [line.rstrip('\n\r') for line in old_block],
                    "new_lines": [line.rstrip('\n\r') for line in new_block]
                })
            elif tag == 'delete':
                # Lines deleted
                old_block = old_lines[old_start:old_end]
                changes.append({
                    "type": "delete",
                    "old_start": old_start + 1,
                    "old_end": old_end,
                    "old_lines": [line.rstrip('\n\r') for line in old_block]
                })
            elif tag == 'insert':
                # Lines inserted
                new_block = new_lines[new_start:new_end]
                changes.append({
                    "type": "insert",
                    "new_start": new_start + 1,
                    "new_end": new_end,
                    "new_lines": [line.rstrip('\n\r') for line in new_block]
                })
        
        # Compute statistics
        stats = self._compute_diff_stats(old_lines, new_lines, changes)
        
        # Generate minimal patch string
        patch_lines = []
        patch_lines.append(f"--- {file_path}")
        patch_lines.append(f"+++ {file_path}")
        
        for change in changes:
            if change["type"] == "replace":
                patch_lines.append(f"@@ -{change['old_start']},{change['old_end'] - change['old_start']} +{change['new_start']},{change['new_end'] - change['new_start']} @@")
                for line in change["old_lines"]:
                    patch_lines.append(f"-{line}")
                for line in change["new_lines"]:
                    patch_lines.append(f"+{line}")
            elif change["type"] == "delete":
                patch_lines.append(f"@@ -{change['old_start']},{change['old_end'] - change['old_start']} +{change['old_start']},0 @@")
                for line in change["old_lines"]:
                    patch_lines.append(f"-{line}")
            elif change["type"] == "insert":
                patch_lines.append(f"@@ -{change['new_start']},0 +{change['new_start']},{change['new_end'] - change['new_start']} @@")
                for line in change["new_lines"]:
                    patch_lines.append(f"+{line}")
        
        patch = '\n'.join(patch_lines)
        
        return {
            "patch": patch,
            "changes": changes,
            "stats": stats
        }
    
    def _compute_diff_stats(
        self,
        old_lines: List[str],
        new_lines: List[str],
        changes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Compute diff statistics."""
        total_old_lines = len(old_lines)
        total_new_lines = len(new_lines)
        
        lines_added = 0
        lines_removed = 0
        lines_modified = 0
        
        for change in changes:
            if change["type"] == "insert":
                lines_added += len(change.get("new_lines", []))
            elif change["type"] == "delete":
                lines_removed += len(change.get("old_lines", []))
            elif change["type"] == "replace":
                old_count = len(change.get("old_lines", []))
                new_count = len(change.get("new_lines", []))
                lines_modified += min(old_count, new_count)
                if new_count > old_count:
                    lines_added += new_count - old_count
                elif old_count > new_count:
                    lines_removed += old_count - new_count
        
        change_percentage = (lines_added + lines_removed + lines_modified) / total_old_lines * 100 if total_old_lines > 0 else 0
        
        return {
            "total_old_lines": total_old_lines,
            "total_new_lines": total_new_lines,
            "lines_added": lines_added,
            "lines_removed": lines_removed,
            "lines_modified": lines_modified,
            "change_percentage": round(change_percentage, 2),
            "is_large_change": change_percentage > 50  # More than 50% changed
        }
    
    def validate_diff(
        self,
        old_content: str,
        new_content: str,
        patch: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate that a diff can be applied cleanly.
        
        Args:
            old_content: Original content
            new_content: New content
            patch: Optional patch to validate
            
        Returns:
            Dict with validation results
        """
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        
        # Check if diff is too large
        total_lines = len(old_lines)
        changed_lines = sum(1 for o, n in zip(old_lines, new_lines) if o != n)
        change_percentage = (changed_lines / total_lines * 100) if total_lines > 0 else 0
        
        # Check for potential conflicts
        potential_conflicts = []
        
        # If patch is provided, try to validate it
        if patch:
            try:
                # Try applying the patch to see if there are conflicts
                test_result, success = self.apply_patch(old_content, patch)
                if not success:
                    potential_conflicts.append({
                        "type": "patch_application_failed",
                        "message": "Patch could not be applied cleanly"
                    })
                elif test_result != new_content:
                    potential_conflicts.append({
                        "type": "patch_mismatch",
                        "message": "Patch result doesn't match expected new_content"
                    })
            except Exception as e:
                potential_conflicts.append({
                    "type": "patch_validation_error",
                    "message": f"Error validating patch: {str(e)}"
                })
        
        # If more than 50% changed, suggest full rewrite
        diff_too_large = change_percentage > 50
        
        return {
            "valid": len(potential_conflicts) == 0,
            "diff_too_large": diff_too_large,
            "potential_conflicts": potential_conflicts,
            "change_percentage": round(change_percentage, 2),
            "changed_lines": changed_lines,
            "total_lines": total_lines
        }
    
    def apply_patch(
        self,
        old_content: str,
        patch: str
    ) -> Tuple[str, bool]:
        """
        Apply a patch to content with improved conflict detection.
        
        Args:
            old_content: Original content
            patch: Patch string to apply
            
        Returns:
            Tuple of (new_content, success)
        """
        try:
            old_lines = old_content.splitlines(keepends=True)
            new_lines = old_lines.copy()
            
            # Parse patch and apply changes
            patch_lines = patch.split('\n')
            i = 0
            conflicts = []
            
            while i < len(patch_lines):
                line = patch_lines[i]
                
                # Skip header lines
                if line.startswith('---') or line.startswith('+++'):
                    i += 1
                    continue
                
                # Match hunk header: @@ -old_start,old_count +new_start,new_count @@
                hunk_match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
                if hunk_match:
                    old_start = int(hunk_match.group(1)) - 1  # Convert to 0-indexed
                    old_count = int(hunk_match.group(2)) if hunk_match.group(2) else 0
                    new_start = int(hunk_match.group(3)) - 1
                    new_count = int(hunk_match.group(4)) if hunk_match.group(4) else 0
                    
                    i += 1
                    hunk_lines = []
                    
                    # Read hunk lines
                    while i < len(patch_lines) and not patch_lines[i].startswith('@@'):
                        hunk_lines.append(patch_lines[i])
                        i += 1
                    
                    # Validate context lines match
                    context_matched = True
                    context_idx = 0
                    for hunk_line in hunk_lines:
                        if hunk_line.startswith(' '):
                            # Context line - should match original
                            expected_line = hunk_line[1:]  # Remove leading space
                            actual_idx = old_start + context_idx
                            if actual_idx < len(old_lines):
                                actual_line = old_lines[actual_idx].rstrip('\n\r')
                                if actual_line != expected_line:
                                    context_matched = False
                                    conflicts.append({
                                        "line": actual_idx + 1,
                                        "expected": expected_line,
                                        "actual": actual_line,
                                        "message": "Context mismatch - file may have been modified"
                                    })
                                    break
                            context_idx += 1
                        elif hunk_line.startswith('-'):
                            # Deleted line
                            context_idx += 1
                        elif hunk_line.startswith('+'):
                            # Added line - don't increment context_idx
                            pass
                    
                    if not context_matched:
                        logger.warning(f"Context mismatch in patch at line {old_start + 1}, skipping hunk")
                        continue
                    
                    # Apply hunk - collect deletions and insertions
                    deletions = []
                    insertions = []
                    current_pos = old_start
                    
                    for hunk_line in hunk_lines:
                        if hunk_line.startswith('-'):
                            # Mark for deletion
                            if current_pos < len(new_lines):
                                deletions.append(current_pos)
                            current_pos += 1
                        elif hunk_line.startswith('+'):
                            # Mark for insertion
                            insertions.append((current_pos, hunk_line[1:]))
                        elif hunk_line.startswith(' '):
                            # Context line - keep it, move position
                            current_pos += 1
                    
                    # Apply deletions (in reverse to maintain indices)
                    for pos in sorted(deletions, reverse=True):
                        if pos < len(new_lines):
                            del new_lines[pos]
                    
                    # Adjust insertion positions to account for deletions
                    # Each deletion before an insertion shifts that insertion position down by 1
                    adjusted_insertions = []
                    for pos, content in insertions:
                        # Count how many deletions occurred before this insertion position
                        deletions_before = sum(1 for d in deletions if d < pos)
                        adjusted_pos = pos - deletions_before
                        adjusted_insertions.append((adjusted_pos, content))
                    
                    # Apply insertions (in forward order, using adjusted positions)
                    for pos, content in sorted(adjusted_insertions, key=lambda x: x[0]):
                        # Ensure newline if needed
                        if not content.endswith('\n') and not content.endswith('\r'):
                            content += '\n'
                        new_lines.insert(pos, content)
                    
                else:
                    i += 1
            
            if conflicts:
                logger.warning(f"Found {len(conflicts)} conflicts while applying patch")
                # Still return the result, but log conflicts
            
            new_content = ''.join(new_lines)
            return new_content, True
            
        except Exception as e:
            logger.error(f"Error applying patch: {e}", exc_info=True)
            return old_content, False
    
    def compute_multi_file_diff(
        self,
        file_changes: Dict[str, Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Compute diff for multiple files.
        
        Args:
            file_changes: Dict mapping file_path to {"old": old_content, "new": new_content}
            
        Returns:
            Dict with diffs for each file
        """
        results = {}
        
        for file_path, contents in file_changes.items():
            old_content = contents.get("old", "")
            new_content = contents.get("new", "")
            
            diff = self.compute_unified_diff(old_content, new_content, file_path)
            minimal = self.compute_minimal_patch(old_content, new_content, file_path)
            
            results[file_path] = {
                "unified_diff": diff,
                "minimal_patch": minimal["patch"],
                "changes": minimal["changes"],
                "stats": minimal["stats"]
            }
        
        return {
            "files": results,
            "total_files": len(results),
            "total_changes": sum(r["stats"]["lines_added"] + r["stats"]["lines_removed"] for r in results.values())
        }

