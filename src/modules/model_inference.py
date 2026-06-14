import src.modules.configurations as cfg
from src.modules.configurations import dbg_print
from src.modules.backend import (
    get_active_backend,
    create_backend,
    shutdown_backend,
)


def chat_completion(
    messages,
    temperature=None,
    max_tokens=None,
    top_p=None,
    top_k=None,
    chat_template_kwargs=None,
):
    if temperature is None:
        temperature = getattr(cfg, "TEMPERATURE", 0.7)
    if max_tokens is None:
        max_tokens = getattr(cfg, "MAX_TOKENS", 512)

    backend = get_active_backend()
    if backend is None:
        return None
    backend.start()
    return backend.chat_completion(
        messages,
        temperature,
        max_tokens,
        top_p,
        top_k,
        chat_template_kwargs,
        model_name=cfg.get_effective_model_id(),
    )


def chat_completion_stream(
    messages,
    temperature=None,
    max_tokens=None,
    top_p=None,
    top_k=None,
    chat_template_kwargs=None,
    tools=None,
):
    if temperature is None:
        temperature = getattr(cfg, "TEMPERATURE", 0.7)
    if max_tokens is None:
        max_tokens = getattr(cfg, "MAX_TOKENS", 512)

    dbg_print(
        f"[INFER] chat_completion_stream -- "
        f"backend={cfg.BACKEND_TYPE} model={cfg.get_effective_model_id()}"
    )
    backend = get_active_backend()
    if backend is None:
        dbg_print(f"[INFER] chat_completion_stream -- NO BACKEND!")
        return
    dbg_print(f"[INFER] Calling backend.start()...")
    backend.start()
    dbg_print(f"[INFER] Calling backend.chat_completion_stream()...")
    yield from backend.chat_completion_stream(
        messages,
        temperature,
        max_tokens,
        top_p,
        top_k,
        chat_template_kwargs,
        model_name=cfg.get_effective_model_id(),
        tools=tools,
    )


def get_llm():
    backend = create_backend()
    return backend.start()


def cleanup():
    shutdown_backend()
