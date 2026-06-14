import json
import src.modules.configurations as configurations
import src.modules.memory as memory


def get_memory() -> dict:
    try:
        history = memory.load_memory()
        return {'messages': history}
    except Exception as exc:
        return {'error': str(exc)}
