from typing import Any, Dict, List
import json
from app.core.agent.base import AgentPlugin
from app.core.services.file_service import FileService

class FileEditorPlugin(AgentPlugin):
    def __init__(self, workspace_dir: str = None):
        self.service = FileService(workspace_dir)

    @property
    def name(self) -> str:
        return "FileEditor"

    @property
    def description(self) -> str:
        return "Tools for reading, writing, and editing files in the local workspace."

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "read_file",
                "func": self.read_file,
                "description": "Read the content of a file. Returns file content and metadata."
            },
            {
                "name": "write_file",
                "func": self.write_file,
                "description": "Write content to a file. Overwrites existing content."
            },
            {
                "name": "replace_text",
                "func": self.replace_text,
                "description": "Replace specific text in a file with new text."
            },
            {
                "name": "list_files",
                "func": self.list_files,
                "description": "List files in a directory."
            }
        ]

    def read_file(self, file_path: str) -> str:
        """
        Reads a file from the given path.
        """
        result = self.service.read_file(file_path)
        if result["success"]:
            return f"File Content ({file_path}):\n{result.get('content')}"
        else:
            return f"Error reading file: {result.get('error')}"

    def write_file(self, file_path: str, content: str) -> str:
        """
        Writes content to a file at the given path.
        """
        result = self.service.write_file(file_path, content)
        if result["success"]:
            return f"Successfully wrote to {file_path}. Size: {result.get('size')} bytes."
        else:
            return f"Error writing file: {result.get('error')}"

    def replace_text(self, file_path: str, old_text: str, new_text: str) -> str:
        """
        Replaces occurrences of old_text with new_text in the specified file.
        """
        result = self.service.replace_text(file_path, old_text, new_text)
        if result.get("success"):
            return f"Successfully replaced text in {file_path}."
        else:
            return f"Error replacing text: {result.get('error')}"

    def list_files(self, directory: str = ".") -> str:
        """
        Lists files in the specified directory (default is current directory).
        """
        # Resolve '.' to workspace root or current working dir if needed
        # Service handles relative paths from workspace root usually, or absolute paths
        result = self.service.list_files(directory)
        if result["success"]:
            files = result.get("files", [])
            count = result.get("count", 0)
            return f"Files in '{directory}': {', '.join(files)} (Total: {count})"
        else:
            return f"Error listing files: {result.get('error')}"
