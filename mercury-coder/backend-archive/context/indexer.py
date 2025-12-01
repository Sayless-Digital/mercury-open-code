from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Dict, List, Tuple

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".venv",
    "venv",
    "coverage",
    ".cache",
}

TEXT_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".json",
    ".md",
    ".txt",
    ".vue",
    ".html",
    ".css",
    ".scss",
    ".yml",
    ".yaml",
    ".ini",
    ".sh",
    ".bash",
    ".rs",
    ".go",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
}


@dataclass
class SearchMatch:
    path: str
    preview: str
    line: int
    size: int
    modified: float


class ProjectIndexer:
    """
    Builds lightweight search indexes for a project directory and executes
    quick substring lookups over the cached snippets.
    """

    def __init__(self, cache_dir: str, file_graph=None):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self.file_graph = file_graph  # Optional FileGraph instance

    def build_index(self, project_path: str, max_files: int = 4000, snippet_chars: int = 4000) -> Dict[str, int]:
        normalized = self._normalize_path(project_path)
        files_indexed: List[Dict[str, object]] = []
        count = 0

        for root, dirs, files in os.walk(normalized):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
            rel_root = os.path.relpath(root, normalized)
            for filename in files:
                if count >= max_files:
                    break
                if filename.startswith("."):
                    continue
                ext = os.path.splitext(filename)[1].lower()
                if ext not in TEXT_EXTENSIONS:
                    continue
                full_path = os.path.join(root, filename)
                rel_path = os.path.normpath(os.path.join(rel_root, filename)).lstrip("./")
                size = os.path.getsize(full_path)
                if size > 250_000:  # skip large files
                    continue
                snippet = self._read_snippet(full_path, snippet_chars)
                files_indexed.append(
                    {
                        "path": rel_path,
                        "size": size,
                        "modified": os.path.getmtime(full_path),
                        "snippet": snippet,
                    }
                )
                
                # Add to file graph if available
                if self.file_graph:
                    try:
                        # Read full content for graph building
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            file_content = f.read()
                        self.file_graph.add_file(rel_path, file_content)
                    except Exception as e:
                        # Silently continue if file can't be read for graph
                        pass
                
                count += 1
            if count >= max_files:
                break

        payload = {"project": normalized, "files": files_indexed}
        cache_file = self._cache_file_for(normalized)
        with open(cache_file, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)

        # Build graph relationships if file_graph is available
        graph_stats = None
        if self.file_graph:
            try:
                graph_stats = self.file_graph.build_graph(normalized)
            except Exception as e:
                # Log but don't fail indexing if graph building fails
                import logging
                logging.getLogger("mercury.context.indexer").warning(f"File graph building failed: {e}")

        result = {"files_indexed": count, "cache_file": cache_file}
        if graph_stats:
            result["graph_stats"] = graph_stats
        
        return result

    def search(self, project_path: str, query: str, limit: int = 5) -> List[SearchMatch]:
        normalized = self._normalize_path(project_path)
        index = self._load_index(normalized)
        lower_query = query.lower()
        matches: List[SearchMatch] = []

        for entry in index:
            snippet = entry.get("snippet", "")
            if lower_query in snippet.lower():
                line = self._estimate_line(snippet, lower_query)
                matches.append(
                    SearchMatch(
                        path=entry["path"],
                        preview=self._highlight(snippet, query),
                        line=line,
                        size=int(entry.get("size", 0)),
                        modified=float(entry.get("modified", 0)),
                    )
                )
            if len(matches) >= limit:
                break

        if len(matches) < limit:
            additional = self._scan_files(normalized, index, lower_query, query, limit - len(matches))
            matches.extend(additional)

        return matches[:limit]

    def _scan_files(
        self,
        project_path: str,
        index: List[Dict[str, object]],
        lower_query: str,
        display_query: str,
        remaining: int,
    ) -> List[SearchMatch]:
        extra_matches: List[SearchMatch] = []
        for entry in index:
            if remaining <= 0:
                break
            full_path = os.path.join(project_path, entry["path"])
            preview, line = self._read_full_excerpt(full_path, lower_query, display_query)
            if preview:
                extra_matches.append(
                    SearchMatch(
                        path=entry["path"],
                        preview=preview,
                        line=line,
                        size=int(entry.get("size", 0)),
                        modified=float(entry.get("modified", 0)),
                    )
                )
                remaining -= 1
        return extra_matches

    def _cache_file_for(self, project_path: str) -> str:
        digest = hashlib.sha1(project_path.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, f"context_{digest}.json")

    def _load_index(self, project_path: str) -> List[Dict[str, object]]:
        cache_file = self._cache_file_for(project_path)
        if not os.path.exists(cache_file):
            raise FileNotFoundError("Project index not built yet.")
        with open(cache_file, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data.get("files", [])

    def _normalize_path(self, project_path: str) -> str:
        if not project_path:
            raise ValueError("project_path is required")
        normalized = os.path.abspath(project_path)
        if not os.path.isdir(normalized):
            raise ValueError(f"Project path does not exist: {project_path}")
        return normalized

    def _read_snippet(self, path: str, limit: int) -> str:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                return handle.read(limit)
        except OSError:
            return ""

    def _read_full_excerpt(self, path: str, lower_query: str, display_query: str) -> Tuple[str, int]:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                lines = handle.readlines()
        except OSError:
            return "", 0

        for idx, line in enumerate(lines):
            if lower_query in line.lower():
                start = max(0, idx - 3)
                end = min(len(lines), idx + 4)
                excerpt = "".join(lines[start:end])
                highlighted = self._highlight(excerpt, display_query)
                return highlighted, idx + 1
        return "", 0

    def _estimate_line(self, snippet: str, lower_query: str) -> int:
        before = snippet.lower().split(lower_query)[0]
        return before.count("\n") + 1

    def _highlight(self, text: str, query: str) -> str:
        try:
            return text.replace(query, f"**{query}**")
        except ValueError:
            return text


