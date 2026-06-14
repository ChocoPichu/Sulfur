import os
import src.modules.configurations as configurations
import ast


def load_identity():
    if os.path.exists(configurations.IDENTITY_FILE):
        with open(configurations.IDENTITY_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            return f"CRITICAL INSTRUCTIONS: {content}"
    return "Error: identity.md is missing."


def read_sandbox(filepath=None):
    try:
        path = filepath or configurations.CURRENT_TARGET_PATH
        if not path:
            return "Error: No target file set."
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"


def write_sandbox(new_data, filepath=None):
    path = filepath or configurations.CURRENT_TARGET_PATH
    if not path:
        return
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_data)
