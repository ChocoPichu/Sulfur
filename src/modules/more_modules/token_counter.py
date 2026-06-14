import src.modules.configurations as cfg
import src.modules.memory as memory


def count_tokens(text: str) -> int:
    return len(text) // 4


def get_current_context_usage() -> int:
    messages = memory.load_memory()

    total_text = ""
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total_text += content

    return count_tokens(total_text)
