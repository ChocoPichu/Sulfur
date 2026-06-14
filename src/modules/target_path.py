import os
import src.modules.configurations as configurations
import src.modules.memory as memory


def set_current_target(path: str):
    if not path:
        configurations.CURRENT_TARGET_PATH = None
        memory.save_memory(memory.load_memory(), target_path=None)
        return True

    path = os.path.expanduser(path)
    if not os.path.isabs(path):
        path = os.path.join(configurations.BASE_DIR, path)
    path = os.path.abspath(path)

    required_extension = configurations.SUPPORTED_LANGUAGES.get(
        configurations.TARGET_LANGUAGE, ".py"
    )

    if not os.path.exists(path) or not path.lower().endswith(
        required_extension
    ):
        return False

    configurations.CURRENT_TARGET_PATH = path
    memory.save_memory(memory.load_memory(), target_path=path)
    return True


def get_current_target():
    return configurations.CURRENT_TARGET_PATH


def add_workspace_file(path: str) -> bool:
    if not path:
        return False

    path = os.path.expanduser(path)
    if not os.path.isabs(path):
        path = os.path.join(configurations.BASE_DIR, path)
    path = os.path.abspath(path)

    if not os.path.exists(path):
        return False

    if path not in configurations.ACTIVE_WORKSPACE_FILES:
        configurations.ACTIVE_WORKSPACE_FILES.append(path)

    return True


def remove_workspace_file(path: str):
    if path in configurations.ACTIVE_WORKSPACE_FILES:
        configurations.ACTIVE_WORKSPACE_FILES.remove(path)


def get_workspace_files() -> list:
    return configurations.ACTIVE_WORKSPACE_FILES


def clear_workspace_files():
    configurations.ACTIVE_WORKSPACE_FILES.clear()
