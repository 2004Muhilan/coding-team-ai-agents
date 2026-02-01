
import os
import subprocess

# Define the allowed playground directory
PLAYGROUND_DIR = os.path.abspath("agent_playground")

def safe_path(path: str) -> str:
    """
    Ensures that the given path is within the allowed playground directory.
    Returns the absolute path if safe, otherwise raises a ValueError.
    """
    # Resolve the absolute path
    # Using relative path logic to ensure we stay inside playground
    base_path = os.path.abspath(PLAYGROUND_DIR)
    requested_path = os.path.abspath(os.path.join(base_path, path))
    
    if not requested_path.startswith(base_path):
        raise ValueError(f"Access denied: Path '{path}' resolves to '{requested_path}', which is outside the allowed playground directory '{base_path}'.")
    
    return requested_path

def read_file(path: str) -> str:
    """
    Reads the content of a file within the playground directory.
    """
    try:
        target_path = safe_path(path)
        if not os.path.exists(target_path):
            return f"Error: File '{path}' does not exist."
        
        with open(target_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file '{path}': {str(e)}"

def write_file(path: str, content: str) -> str:
    """
    Writes content to a file within the playground directory.
    Creates parent directories if they don't exist.
    """
    try:
        target_path = safe_path(path)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        return f"Successfully wrote to '{path}'."
    except Exception as e:
        return f"Error writing to file '{path}': {str(e)}"

def list_files(path: str = ".") -> str:
    """
    Lists files in a directory recursively.
    """
    try:
        target_path = safe_path(path)
        if not os.path.exists(target_path):
            return f"Error: Path '{path}' does not exist."
        
        # Ensure playground exists
        os.makedirs(PLAYGROUND_DIR, exist_ok=True)
        
        # Execute ls -R
        # We use strict arguments to avoid command injection, although safe_path validates the location.
        command = ["ls", "-R", target_path]
        
        result = subprocess.run(
            command,
            cwd=PLAYGROUND_DIR, # run from playground root generally, but ls target_path works if target_path is absolute or relative
            # Since safe_path returns absolute path, we can just pass it to ls
            shell=False,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        output = result.stdout
        if result.stderr:
            output += "\nStderr:\n" + result.stderr
        
        return output if output else "(no output)"
            
    except Exception as e:
        return f"Error listing files in '{path}': {str(e)}"

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from the playground",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file in the playground",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file"},
                    "content": {"type": "string", "description": "Content to write"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in a directory recursively",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the directory (default: '.')"}
                },
                "required": ["path"]
            }
        }
    }
]

AVAILABLE_FUNCTIONS = {
    "read_file": read_file,
    "write_file": write_file,
    "list_files": list_files,
}
