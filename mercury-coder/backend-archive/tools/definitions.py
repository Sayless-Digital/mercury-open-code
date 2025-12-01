"""
Tool definitions for Claude's native tool calling.
Each tool follows Anthropic's tool specification format.
"""

TOOL_DEFINITIONS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file. Use this to examine code, configuration files, or any text file in the project.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to read, relative to the project root or absolute path"
                }
            },
            "required": ["file_path"],
            "additionalProperties": False
        }
    },
    {
        "name": "write_file",
        "description": "Write content to a file. Creates the file if it doesn't exist, overwrites if it does. Use this to create new files or completely replace existing files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to write, relative to the project root or absolute path"
                },
                "content": {
                    "type": "string",
                    "description": "The complete content to write to the file"
                }
            },
            "required": ["file_path", "content"],
            "additionalProperties": False
        }
    },
    {
        "name": "edit_file",
        "description": "Edit a file by applying a diff or making targeted changes. Use this to modify existing files without replacing the entire content. Supports search-and-replace operations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to edit, relative to the project root or absolute path"
                },
                "old_string": {
                    "type": "string",
                    "description": "The exact text to replace (must match exactly, including whitespace)"
                },
                "new_string": {
                    "type": "string",
                    "description": "The replacement text"
                }
            },
            "required": ["file_path", "old_string", "new_string"],
            "additionalProperties": False
        }
    },
    {
        "name": "list_directory",
        "description": "List files and directories in a given path. Use this to explore the project structure, find files, or understand the codebase organization.",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory_path": {
                    "type": "string",
                    "description": "Path to the directory to list, relative to the project root or absolute path. Use '.' for current directory or empty string for project root."
                }
            },
            "required": ["directory_path"],
            "additionalProperties": False
        }
    },
    {
        "name": "execute_command",
        "description": "Execute a shell command in the project directory. Use this to run build commands, tests, install packages, or any CLI operations. Be careful with destructive commands.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute (e.g., 'npm install', 'python test.py', 'git status')"
                },
                "cwd": {
                    "type": "string",
                    "description": "Working directory for the command (optional, defaults to project root)"
                }
            },
            "required": ["command"],
            "additionalProperties": False
        }
    },
    {
        "name": "codebase_search",
        "description": "Search the codebase for code patterns, functions, classes, or text. This performs semantic and keyword search across all files in the project.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query - can be code patterns, function names, class names, or descriptive text"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 10)",
                    "default": 10
                }
            },
            "required": ["query"],
            "additionalProperties": False
        }
    },
    {
        "name": "grep",
        "description": "Search for text patterns in files using regex. Use this to find specific code patterns, function calls, or text across multiple files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regex pattern to search for"
                },
                "file_path": {
                    "type": "string",
                    "description": "File or directory path to search in (optional, searches entire project if not specified)"
                }
            },
            "required": ["pattern"],
            "additionalProperties": False
        }
    },
    {
        "name": "delete_file",
        "description": "Delete a file. Use this to remove files that are no longer needed. Be careful - this action cannot be undone.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to delete, relative to the project root or absolute path"
                }
            },
            "required": ["file_path"],
            "additionalProperties": False
        }
    },
    {
        "name": "delete_directory",
        "description": "Delete a directory and optionally all its contents recursively. Use this to remove directories. Be careful - this action cannot be undone.",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory_path": {
                    "type": "string",
                    "description": "Path to the directory to delete, relative to the project root or absolute path"
                },
                "recursive": {
                    "type": "boolean",
                    "description": "If true, delete the directory and all its contents. If false, only delete if the directory is empty (default: true)",
                    "default": True
                }
            },
            "required": ["directory_path"],
            "additionalProperties": False
        }
    },
    {
        "name": "create_directory",
        "description": "Create a directory (folder). Creates parent directories if they don't exist.",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory_path": {
                    "type": "string",
                    "description": "Path to the directory to create, relative to the project root or absolute path"
                }
            },
            "required": ["directory_path"],
            "additionalProperties": False
        }
    },
    {
        "name": "move_file",
        "description": "Move or rename a file or directory. Use this to reorganize files or rename them.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source_path": {
                    "type": "string",
                    "description": "Path to the file or directory to move/rename, relative to the project root or absolute path"
                },
                "destination_path": {
                    "type": "string",
                    "description": "Destination path for the file or directory, relative to the project root or absolute path"
                }
            },
            "required": ["source_path", "destination_path"],
            "additionalProperties": False
        }
    },
    {
        "name": "copy_file",
        "description": "Copy a file or directory to a new location. For directories, copies recursively.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source_path": {
                    "type": "string",
                    "description": "Path to the file or directory to copy, relative to the project root or absolute path"
                },
                "destination_path": {
                    "type": "string",
                    "description": "Destination path for the copy, relative to the project root or absolute path"
                }
            },
            "required": ["source_path", "destination_path"],
            "additionalProperties": False
        }
    },
    {
        "name": "file_exists",
        "description": "Check if a file or directory exists at the given path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to check, relative to the project root or absolute path"
                }
            },
            "required": ["path"],
            "additionalProperties": False
        }
    },
    {
        "name": "get_file_info",
        "description": "Get metadata about a file or directory, including size, modification time, and type.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file or directory, relative to the project root or absolute path"
                }
            },
            "required": ["path"],
            "additionalProperties": False
        }
    },
    {
        "name": "find_files",
        "description": "Find files in the project by pattern, extension, or name. Use this to locate specific types of files (e.g., all .py files, all test files).",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "File pattern to search for. Can be a glob pattern (e.g., '*.py', 'test_*.js') or a partial filename"
                },
                "directory_path": {
                    "type": "string",
                    "description": "Directory to search in (optional, searches entire project if not specified)"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 50)",
                    "default": 50
                }
            },
            "required": ["pattern"],
            "additionalProperties": False
        }
    },
    {
        "name": "read_directory_tree",
        "description": "Get a tree view of a directory structure. Shows the hierarchical structure of files and folders.",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory_path": {
                    "type": "string",
                    "description": "Path to the directory to visualize, relative to the project root or absolute path. Use '.' for current directory."
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum depth to traverse (default: 5, use -1 for unlimited)",
                    "default": 5
                },
                "include_hidden": {
                    "type": "boolean",
                    "description": "Whether to include hidden files and directories (default: false)",
                    "default": False
                }
            },
            "required": ["directory_path"],
            "additionalProperties": False
        }
    },
    {
        "name": "read_env_file",
        "description": "Read environment variables from a .env file. Returns key-value pairs of environment variables.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the .env file (default: '.env' in project root)",
                    "default": ".env"
                }
            },
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "name": "write_env_file",
        "description": "Write environment variables to a .env file. Can update existing variables or add new ones.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the .env file (default: '.env' in project root)",
                    "default": ".env"
                },
                "variables": {
                    "type": "object",
                    "description": "Dictionary of environment variable key-value pairs to write",
                    "additionalProperties": {
                        "type": "string"
                    }
                },
                "merge": {
                    "type": "boolean",
                    "description": "If true, merge with existing variables. If false, replace entire file (default: true)",
                    "default": True
                }
            },
            "required": ["variables"],
            "additionalProperties": False
        }
    },
    {
        "name": "search_replace_in_multiple_files",
        "description": "Search and replace text across multiple files. Use this to make the same change in multiple files at once.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "The text pattern to search for (exact match or regex)"
                },
                "replacement": {
                    "type": "string",
                    "description": "The replacement text"
                },
                "file_pattern": {
                    "type": "string",
                    "description": "File pattern to match (e.g., '*.py', '*.js') or directory path to search in (optional, searches all files if not specified)"
                },
                "use_regex": {
                    "type": "boolean",
                    "description": "Whether to treat pattern as regex (default: false)",
                    "default": False
                }
            },
            "required": ["pattern", "replacement"],
            "additionalProperties": False
        }
    },
    {
        "name": "git_status",
        "description": "Check the status of the git repository. Shows modified, staged, and untracked files.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "name": "git_add",
        "description": "Stage files for commit. Add files to the git staging area.",
        "input_schema": {
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "List of file paths to stage. Use '.' to stage all changes, or specific file paths."
                }
            },
            "required": ["files"],
            "additionalProperties": False
        }
    },
    {
        "name": "git_commit",
        "description": "Commit staged changes to the repository. Creates a new commit with the staged files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Commit message describing the changes"
                }
            },
            "required": ["message"],
            "additionalProperties": False
        }
    },
    {
        "name": "git_push",
        "description": "Push commits to the remote repository. Uploads local commits to the remote.",
        "input_schema": {
            "type": "object",
            "properties": {
                "remote": {
                    "type": "string",
                    "description": "Remote name (default: 'origin')",
                    "default": "origin"
                },
                "branch": {
                    "type": "string",
                    "description": "Branch name to push (optional, uses current branch if not specified)"
                }
            },
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "name": "git_pull",
        "description": "Pull changes from the remote repository. Downloads and merges remote changes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "remote": {
                    "type": "string",
                    "description": "Remote name (default: 'origin')",
                    "default": "origin"
                },
                "branch": {
                    "type": "string",
                    "description": "Branch name to pull (optional, uses current branch if not specified)"
                }
            },
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "name": "git_branch",
        "description": "List, create, or switch git branches. Manage branches in the repository.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action to perform: 'list' (list all branches), 'create' (create new branch), 'switch' (switch to branch), 'delete' (delete branch)",
                    "enum": ["list", "create", "switch", "delete"]
                },
                "branch_name": {
                    "type": "string",
                    "description": "Branch name (required for create, switch, and delete actions)"
                }
            },
            "required": ["action"],
            "additionalProperties": False
        }
    },
    {
        "name": "git_log",
        "description": "View git commit history. Shows recent commits with messages, authors, and dates.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of commits to show (default: 10)",
                    "default": 10
                },
                "branch": {
                    "type": "string",
                    "description": "Branch to show log for (optional, uses current branch if not specified)"
                }
            },
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "name": "git_diff",
        "description": "Show differences between commits, branches, or working directory. View what has changed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Specific file to show diff for (optional, shows all changes if not specified)"
                },
                "staged": {
                    "type": "boolean",
                    "description": "Show staged changes instead of unstaged (default: false)",
                    "default": False
                },
                "commit": {
                    "type": "string",
                    "description": "Show diff for a specific commit (optional)"
                }
            },
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "name": "http_request",
        "description": "Make HTTP requests (GET, POST, PUT, DELETE, etc.). Use this to test APIs, fetch data from URLs, or interact with web services.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to make the request to"
                },
                "method": {
                    "type": "string",
                    "description": "HTTP method (GET, POST, PUT, DELETE, PATCH, etc.)",
                    "default": "GET",
                    "enum": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
                },
                "headers": {
                    "type": "object",
                    "description": "HTTP headers to include in the request",
                    "additionalProperties": {
                        "type": "string"
                    }
                },
                "body": {
                    "type": "string",
                    "description": "Request body (for POST, PUT, PATCH requests). Can be JSON string or plain text"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Request timeout in seconds (default: 30)",
                    "default": 30
                }
            },
            "required": ["url"],
            "additionalProperties": False
        }
    },
    {
        "name": "read_json_file",
        "description": "Read and parse a JSON file. Returns the parsed JSON object. Use this for package.json, tsconfig.json, and other JSON configuration files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the JSON file to read, relative to the project root or absolute path"
                }
            },
            "required": ["file_path"],
            "additionalProperties": False
        }
    },
    {
        "name": "write_json_file",
        "description": "Write data to a JSON file with proper formatting. Use this to create or update JSON configuration files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the JSON file to write, relative to the project root or absolute path"
                },
                "data": {
                    "type": "object",
                    "description": "The JSON data to write (as an object/dictionary)"
                },
                "indent": {
                    "type": "integer",
                    "description": "Number of spaces for indentation (default: 2)",
                    "default": 2
                }
            },
            "required": ["file_path", "data"],
            "additionalProperties": False
        }
    },
    {
        "name": "read_yaml_file",
        "description": "Read and parse a YAML file. Returns the parsed YAML object. Use this for docker-compose.yml, .github/workflows, and other YAML configuration files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the YAML file to read, relative to the project root or absolute path"
                }
            },
            "required": ["file_path"],
            "additionalProperties": False
        }
    },
    {
        "name": "write_yaml_file",
        "description": "Write data to a YAML file with proper formatting. Use this to create or update YAML configuration files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the YAML file to write, relative to the project root or absolute path"
                },
                "data": {
                    "type": "object",
                    "description": "The YAML data to write (as an object/dictionary)"
                }
            },
            "required": ["file_path", "data"],
            "additionalProperties": False
        }
    },
    {
        "name": "check_syntax",
        "description": "Check the syntax of a code file. Validates that the file has correct syntax for its language. Supports Python, JavaScript, TypeScript, and other languages.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to check, relative to the project root or absolute path"
                },
                "language": {
                    "type": "string",
                    "description": "Programming language (python, javascript, typescript, etc.). If not specified, will be inferred from file extension."
                }
            },
            "required": ["file_path"],
            "additionalProperties": False
        }
    },
    {
        "name": "lint_file",
        "description": "Lint a code file to find potential errors, style issues, and bugs. Uses language-specific linters when available.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to lint, relative to the project root or absolute path"
                },
                "language": {
                    "type": "string",
                    "description": "Programming language (python, javascript, typescript, etc.). If not specified, will be inferred from file extension."
                }
            },
            "required": ["file_path"],
            "additionalProperties": False
        }
    },
    {
        "name": "list_processes",
        "description": "List running processes. Shows processes that match a given name pattern or all processes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Process name pattern to filter by (optional, shows all processes if not specified)"
                }
            },
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "name": "kill_process",
        "description": "Kill a running process by PID or name. Use this to stop processes that are blocking ports or consuming resources.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pid": {
                    "type": "integer",
                    "description": "Process ID (PID) to kill. Either pid or name must be provided."
                },
                "name": {
                    "type": "string",
                    "description": "Process name to kill. Either pid or name must be provided."
                },
                "signal": {
                    "type": "string",
                    "description": "Signal to send (SIGTERM, SIGKILL, etc.). Default: SIGTERM",
                    "default": "SIGTERM",
                    "enum": ["SIGTERM", "SIGKILL", "SIGINT"]
                }
            },
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "name": "check_port",
        "description": "Check if a port is in use. Returns whether the port is available or what process is using it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "port": {
                    "type": "integer",
                    "description": "Port number to check"
                }
            },
            "required": ["port"],
            "additionalProperties": False
        }
    },
    {
        "name": "read_package_json",
        "description": "Read and parse package.json file. Returns dependencies, scripts, and other package information.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to package.json (default: 'package.json' in project root)",
                    "default": "package.json"
                }
            },
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "name": "read_requirements_txt",
        "description": "Read and parse requirements.txt file. Returns list of Python packages and their versions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to requirements.txt (default: 'requirements.txt' in project root)",
                    "default": "requirements.txt"
                }
            },
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "name": "get_installed_packages",
        "description": "Get list of installed packages. Supports npm (Node.js) and pip (Python) package managers.",
        "input_schema": {
            "type": "object",
            "properties": {
                "package_manager": {
                    "type": "string",
                    "description": "Package manager to query (npm, pip, pip3)",
                    "enum": ["npm", "pip", "pip3"]
                }
            },
            "required": ["package_manager"],
            "additionalProperties": False
        }
    },
    {
        "name": "calculate_file_hash",
        "description": "Calculate file hash (checksum). Supports MD5, SHA256, and SHA1 algorithms. Useful for verifying file integrity.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to hash, relative to the project root or absolute path"
                },
                "algorithm": {
                    "type": "string",
                    "description": "Hash algorithm to use (md5, sha256, sha1)",
                    "default": "sha256",
                    "enum": ["md5", "sha256", "sha1"]
                }
            },
            "required": ["file_path"],
            "additionalProperties": False
        }
    },
    {
        "name": "get_environment_variable",
        "description": "Get system environment variable value. Returns the value of an environment variable from the system.",
        "input_schema": {
            "type": "object",
            "properties": {
                "variable_name": {
                    "type": "string",
                    "description": "Name of the environment variable to get"
                }
            },
            "required": ["variable_name"],
            "additionalProperties": False
        }
    },
    {
        "name": "get_file_dependencies",
        "description": "Get files that import or use a given file. Returns dependencies (files this imports) and dependents (files that import this).",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to get dependencies for"
                }
            },
            "required": ["file_path"],
            "additionalProperties": False
        }
    },
    {
        "name": "find_related_files",
        "description": "Find files related to a given file by imports, components, or dependencies. Returns files connected through the dependency graph.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to find related files for"
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum depth to traverse the dependency graph (default: 2)",
                    "default": 2
                }
            },
            "required": ["file_path"],
            "additionalProperties": False
        }
    },
    {
        "name": "get_component_boundaries",
        "description": "Get component structure for a file. Returns React components, Vue components, classes, or other component boundaries.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to get component boundaries for"
                }
            },
            "required": ["file_path"],
            "additionalProperties": False
        }
    },
    {
        "name": "find_similar_patterns",
        "description": "Find code with similar patterns (naming conventions, structure, API usage). Helps discover related code patterns.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern_type": {
                    "type": "string",
                    "description": "Type of pattern to match: 'naming', 'structure', or 'api_usage'",
                    "enum": ["naming", "structure", "api_usage"]
                },
                "file_path": {
                    "type": "string",
                    "description": "Optional file path to compare against. If not provided, searches all files."
                }
            },
            "required": ["pattern_type"],
            "additionalProperties": False
        }
    },
    {
        "name": "generate_diff",
        "description": "Generate a unified diff between old and new file content. Use this to see what changes will be made before applying them. Returns diff in unified format with statistics.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file (for diff header)"
                },
                "old_content": {
                    "type": "string",
                    "description": "Original file content"
                },
                "new_content": {
                    "type": "string",
                    "description": "New file content"
                },
                "format": {
                    "type": "string",
                    "description": "Diff format: 'unified' (unified diff) or 'minimal' (minimal patch)",
                    "enum": ["unified", "minimal"],
                    "default": "unified"
                }
            },
            "required": ["old_content", "new_content"],
            "additionalProperties": False
        }
    },
    {
        "name": "parse_ast",
        "description": "Parse a code file to its Abstract Syntax Tree (AST). Returns structure with classes, functions, imports, and variables. Useful for understanding code structure and finding symbols.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to parse"
                }
            },
            "required": ["file_path"],
            "additionalProperties": False
        }
    },
    {
        "name": "find_references",
        "description": "Find all references to a symbol (function, class, variable) in a file. Returns line numbers and context where the symbol is used.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to search in"
                },
                "symbol": {
                    "type": "string",
                    "description": "Symbol name to find references for"
                }
            },
            "required": ["file_path", "symbol"],
            "additionalProperties": False
        }
    },
    {
        "name": "get_type_info",
        "description": "Get type information for a symbol (function, class, variable). Returns type, definition, and metadata.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file containing the symbol"
                },
                "symbol": {
                    "type": "string",
                    "description": "Symbol name to get type information for"
                }
            },
            "required": ["file_path", "symbol"],
            "additionalProperties": False
        }
    },
    {
        "name": "find_unused_code",
        "description": "Find unused imports, variables, or functions in a file. Helps identify dead code that can be removed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to analyze"
                },
                "check_type": {
                    "type": "string",
                    "description": "What to check: 'imports', 'functions', 'variables', or 'all'",
                    "enum": ["imports", "functions", "variables", "all"],
                    "default": "all"
                }
            },
            "required": ["file_path"],
            "additionalProperties": False
        }
    },
    {
        "name": "detect_potential_bugs",
        "description": "Detect potential bugs and code quality issues using static analysis. Finds common patterns that may cause problems.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to analyze"
                }
            },
            "required": ["file_path"],
            "additionalProperties": False
        }
    },
    {
        "name": "web_search",
        "description": "Search the web using Google or other search engines. Returns search results with titles, URLs, and snippets. Use this to find information, documentation, tutorials, or any web content related to your research query.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query string (e.g., 'Python async await tutorial', 'React hooks documentation')"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of search results to return (default: 10, max: 20)",
                    "default": 10
                }
            },
            "required": ["query"],
            "additionalProperties": False
        }
    },
    {
        "name": "fetch_web_page",
        "description": "Fetch and extract content from a web page. Downloads the HTML, extracts readable text content, and provides metadata. Use this to read the actual content of web pages found in search results or linked from other pages.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL of the web page to fetch"
                },
                "extract_links": {
                    "type": "boolean",
                    "description": "Whether to extract and return links found on the page (default: true)",
                    "default": True
                },
                "max_content_length": {
                    "type": "integer",
                    "description": "Maximum length of extracted text content in characters (default: 50000)",
                    "default": 50000
                }
            },
            "required": ["url"],
            "additionalProperties": False
        }
    },
    {
        "name": "extract_links",
        "description": "Extract all links (URLs) from a web page. Returns a list of links found on the page, including both internal and external links. Use this to discover related pages for deeper research.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL of the web page to extract links from"
                },
                "filter_domain": {
                    "type": "string",
                    "description": "Optional domain to filter links (e.g., 'example.com' to only get links from that domain)"
                },
                "max_links": {
                    "type": "integer",
                    "description": "Maximum number of links to return (default: 50)",
                    "default": 50
                }
            },
            "required": ["url"],
            "additionalProperties": False
        }
    }
]


def get_tool_definitions():
    """
    Get all tool definitions in Claude's native format.
    Returns list of tool dicts ready to pass to invoke_bedrock_model().
    """
    return TOOL_DEFINITIONS



