import json
import os
import re
from typing import Optional

import src.modules.configurations as cfg
import src.modules.target_path as target_path
from src.modules.sandbox_file_operations import (
    read_sandbox,
    write_sandbox,
)

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read the contents of a file "
                "in the workspace."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "The relative or absolute "
                            "path to the file."
                        ),
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Write or overwrite a file "
                "in the workspace. Creates new files "
                "if they don't exist."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "The path to write "
                            "the file to."
                        ),
                    },
                    "content": {
                        "type": "string",
                        "description": (
                            "The full content to write "
                            "to the file."
                        ),
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": (
                "Edit a file using find-and-replace. "
                "Finds the first occurrence of "
                "'old_string' and replaces it with "
                "'new_string'. The old_string must be "
                "unique and match exactly "
                "(including whitespace)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "The path to the file "
                            "to edit."
                        ),
                    },
                    "old_string": {
                        "type": "string",
                        "description": (
                            "The exact text to find "
                            "and replace."
                        ),
                    },
                    "new_string": {
                        "type": "string",
                        "description": (
                            "The replacement text."
                        ),
                    },
                },
                "required": ["path", "old_string", "new_string"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": (
                "List files currently "
                "in the workspace."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": (
                "Search for a pattern in workspace "
                "files. Returns matching file paths "
                "and line numbers."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": (
                            "The text or regex pattern "
                            "to search for."
                        ),
                    },
                    "path": {
                        "type": "string",
                        "description": (
                            "Optional: limit search "
                            "to this directory or file."
                        ),
                    },
                },
                "required": ["pattern"],
            },
        },
    },
]


def execute_tool(name: str, arguments: dict) -> str:
    """Execute a tool call and return the result as a string."""
    if name == "read_file":
        return _tool_read_file(arguments.get("path", ""))
    elif name == "write_file":
        return _tool_write_file(
            arguments.get("path", ""),
            arguments.get("content", ""),
        )
    elif name == "edit_file":
        return _tool_edit_file(
            arguments.get("path", ""),
            arguments.get("old_string", ""),
            arguments.get("new_string", ""),
        )
    elif name == "list_files":
        return _tool_list_files()
    elif name == "search_code":
        return _tool_search_code(
            arguments.get("pattern", ""),
            arguments.get("path"),
        )
    else:
        return f"Error: unknown tool '{name}'"


def _resolve_path(path: str) -> Optional[str]:
    """Resolve a file path relative to the workspace."""
    if not path:
        return None
    if os.path.isabs(path):
        return path
    workspace_files = target_path.get_workspace_files()
    for wf in workspace_files:
        if wf.endswith(path) or os.path.basename(wf) == path:
            return wf
    cwd = getattr(cfg, "BASE_DIR", "")
    candidate = os.path.join(cwd, path)
    if os.path.exists(candidate):
        return candidate
    return path


def _tool_read_file(path: str) -> str:
    resolved = _resolve_path(path)
    if not resolved:
        return "Error: no path provided."
    content = read_sandbox(resolved)
    if content.startswith("Error:"):
        return f"Error reading {path}: {content}"
    return content


def _tool_write_file(path: str, content: str) -> str:
    resolved = _resolve_path(path) or path
    try:
        write_sandbox(content, resolved)
        abs_path = os.path.abspath(resolved)
        if (
            os.path.exists(abs_path)
            and abs_path not in target_path.get_workspace_files()
        ):
            target_path.add_workspace_file(abs_path)
            return (
                f"Successfully wrote {len(content)} characters "
                f"to {resolved} "
                "(auto-registered in workspace)"
            )
        return (
            f"Successfully wrote {len(content)} characters "
            f"to {resolved}"
        )
    except Exception as e:
        return f"Error writing {resolved}: {e}"


def _tool_edit_file(
    path: str, old_string: str, new_string: str
) -> str:
    resolved = _resolve_path(path)
    if not resolved:
        return "Error: no path provided."
    content = read_sandbox(resolved)
    if content.startswith("Error:"):
        return f"Error reading {path}: {content}"

    count = content.count(old_string)
    if count == 0:
        return (
            f"Error: 'old_string' not found in {resolved}. "
            "Double-check the exact text "
            "(including whitespace)."
        )
    if count > 1:
        return (
            f"Error: 'old_string' found {count} times "
            f"in {resolved}. Provide more surrounding "
            "context to make it unique."
        )

    new_content = content.replace(old_string, new_string, 1)
    try:
        write_sandbox(new_content, resolved)
        abs_path = os.path.abspath(resolved)
        if (
            os.path.exists(abs_path)
            and abs_path not in target_path.get_workspace_files()
        ):
            target_path.add_workspace_file(abs_path)
        return f"Successfully edited {resolved}."
    except Exception as e:
        return f"Error writing {resolved}: {e}"


def _tool_list_files() -> str:
    files = target_path.get_workspace_files()
    if not files:
        return "No files in workspace."
    return "Workspace files:\n" + "\n".join(
        f"  - {f}" for f in files
    )


def _tool_search_code(
    pattern: str, path: Optional[str] = None
) -> str:
    files = target_path.get_workspace_files()
    if path:
        resolved = _resolve_path(path)
        if resolved and resolved in files:
            files = [resolved]
        elif resolved:
            if os.path.isdir(resolved):
                files = []
                skip = {
                    ".git",
                    ".venv",
                    "venv",
                    "__pycache__",
                    "node_modules",
                    ".mypy_cache",
                }
                for root, dirs, fnames in os.walk(resolved):
                    dirs[:] = [
                        d for d in dirs
                        if d not in skip
                        and not d.startswith(".")
                    ]
                    for fname in fnames:
                        files.append(
                            os.path.join(root, fname)
                        )
            else:
                files = [resolved]

    if not files:
        return "No files to search."

    results = []
    try:
        regex = re.compile(pattern)
    except re.error:
        regex = re.compile(re.escape(pattern))

    for fpath in files:
        try:
            content = read_sandbox(fpath)
            if content.startswith("Error:"):
                continue
            for lineno, line in enumerate(
                content.split("\n"), 1
            ):
                if regex.search(line):
                    results.append(
                        f"{fpath}:{lineno}: "
                        f"{line.strip()[:120]}"
                    )
        except Exception:
            continue

    if not results:
        return f"No matches found for '{pattern}'."
    return (
        "Matches:\n"
        + "\n".join(results[:50])
        + (
            f"\n... and {len(results) - 50} more"
            if len(results) > 50
            else ""
        )
    )
