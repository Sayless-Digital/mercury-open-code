"""
Tool Registry - centralized tool definitions and groupings for agents.
"""

from typing import List, Dict, Any


class ToolRegistry:
    """
    Centralized registry for tool definitions and groupings.
    
    Provides tool groups for different agent types to avoid duplication.
    """
    
    # Tool groups
    READ_TOOLS = [
        "read_file",
        "list_directory",
        "read_directory_tree",
        "read_json_file",
        "read_yaml_file",
        "read_package_json",
        "read_requirements_txt",
        "read_env_file",
        "get_file_info",
        "file_exists"
    ]
    
    WRITE_TOOLS = [
        "write_file",
        "edit_file",
        "write_json_file",
        "write_yaml_file",
        "write_env_file",
        "create_directory"
    ]
    
    SEARCH_TOOLS = [
        "codebase_search",
        "grep",
        "find_files"
    ]
    
    WEB_RESEARCH_TOOLS = [
        "web_search",
        "fetch_web_page",
        "extract_links",
        "http_request"
    ]
    
    ANALYSIS_TOOLS = [
        "get_file_dependencies",
        "find_related_files",
        "get_component_boundaries",
        "find_similar_patterns"
    ]
    
    VALIDATION_TOOLS = [
        "check_syntax",
        "lint_file",
        "execute_command"
    ]
    
    DIFF_TOOLS = [
        "generate_diff",
        "search_replace_in_multiple_files"
    ]
    
    # Agent-specific tool sets
    PLANNER_TOOLS = READ_TOOLS + SEARCH_TOOLS + ANALYSIS_TOOLS
    
    RESEARCHER_TOOLS = READ_TOOLS + SEARCH_TOOLS + WEB_RESEARCH_TOOLS
    
    CODER_TOOLS = READ_TOOLS + WRITE_TOOLS + SEARCH_TOOLS + DIFF_TOOLS + WEB_RESEARCH_TOOLS
    
    ANALYZER_TOOLS = READ_TOOLS + VALIDATION_TOOLS + SEARCH_TOOLS
    
    @classmethod
    def get_tools_for_agent(cls, agent_name: str) -> List[str]:
        """
        Get tool list for a specific agent.
        
        Args:
            agent_name: Name of the agent (planner, researcher, coder, analyzer)
            
        Returns:
            List of tool names
        """
        tool_map = {
            "planner": cls.PLANNER_TOOLS,
            "researcher": cls.RESEARCHER_TOOLS,
            "coder": cls.CODER_TOOLS,
            "analyzer": cls.ANALYZER_TOOLS
        }
        return tool_map.get(agent_name, [])
    
    @classmethod
    def get_tool_group(cls, group_name: str) -> List[str]:
        """
        Get tools in a specific group.
        
        Args:
            group_name: Name of tool group (READ_TOOLS, WRITE_TOOLS, etc.)
            
        Returns:
            List of tool names in group
        """
        return getattr(cls, group_name, [])
    
    @classmethod
    def get_all_tools(cls) -> List[str]:
        """
        Get all available tools.
        
        Returns:
            List of all tool names
        """
        all_tools = set()
        all_tools.update(cls.READ_TOOLS)
        all_tools.update(cls.WRITE_TOOLS)
        all_tools.update(cls.SEARCH_TOOLS)
        all_tools.update(cls.ANALYSIS_TOOLS)
        all_tools.update(cls.VALIDATION_TOOLS)
        all_tools.update(cls.DIFF_TOOLS)
        return sorted(list(all_tools))

