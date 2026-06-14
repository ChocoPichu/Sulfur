import os
from typing import Optional

from .base import BaseBackend
from .llama_cpp import LlamaCppBackend
from .lm_studio import LMStudioBackend, DEFAULT_LM_STUDIO_URL
from .ollama import OllamaBackend, DEFAULT_OLLAMA_URL
import src.modules.configurations as cfg
from src.modules.configurations import dbg_print

_backend_instance: Optional[BaseBackend] = None
_active_backend_type: Optional[str] = None


def _build_llama_cpp() -> LlamaCppBackend:
    target_model_name = cfg.MODEL_NAME
    model_path_str = cfg.get_model_path()
    if isinstance(model_path_str, dict):
        model_path_str = model_path_str.get("path", "")
    if not model_path_str:
        available = list(cfg.AVAILABLE_MODELS.keys())
        if available:
            fallback = available[0]
            dbg_print(
                f"[BACKEND] Model '{target_model_name}' "
                f"not found in GGUF folder, "
                f"falling back to '{fallback}'"
            )
            cfg.set_model_name(fallback)
            model_path_str = cfg.get_model_path()
            if isinstance(model_path_str, dict):
                model_path_str = model_path_str.get("path", "")
    if not model_path_str:
        raise Exception(
            f"No model path found for "
            f"'{target_model_name}'. "
            f"Valid models are: "
            f"{list(cfg.AVAILABLE_MODELS.keys())}"
        )
    target_model_path = os.path.join(
        cfg.BASE_DIR, model_path_str
    )
    llama_exe = os.path.join(
        cfg.BASE_DIR,
        "bin",
        "llama-cpp-cuda",
        "llama-server.exe",
    )

    return LlamaCppBackend(
        executable_path=llama_exe,
        model_path=target_model_path,
        ctx_size=cfg.NUM_CTX,
        gpu_layers=cfg.GPU_LAYERS,
        flash_attention=cfg.FLASH_ATTENTION,
        prompt_caching=cfg.PROMPT_CACHING,
        mlock=cfg.MLOCK,
        threads=cfg.NUM_THREAD,
        kv_cache_quant=cfg.KV_CACHE_QUANT,
        cpu_moe_layers=cfg.CPU_MOE_LAYERS,
    )


def create_backend() -> BaseBackend:
    global _backend_instance, _active_backend_type
    bt = cfg.BACKEND_TYPE
    dbg_print(
        f"[BACKEND] create_backend() -- "
        f"requested type: {bt}"
    )

    if bt == "llama_cpp":
        _backend_instance = _build_llama_cpp()
    elif bt == "lm_studio":
        url = cfg.BACKEND_URL or DEFAULT_LM_STUDIO_URL
        _backend_instance = LMStudioBackend(url)
    elif bt == "ollama":
        url = cfg.BACKEND_URL or DEFAULT_OLLAMA_URL
        from src.modules.profiles import get_profile

        profile = get_profile(cfg.MODEL_TYPE)
        _backend_instance = OllamaBackend(
            url,
            use_native_api=profile.ollama_uses_native_api,
        )
    else:
        raise ValueError(f"Unknown backend type: {bt}")

    _active_backend_type = bt
    dbg_print(
        f"[BACKEND] create_backend() -> "
        f"{type(_backend_instance).__name__} "
        f"stored (type={bt})"
    )
    return _backend_instance


def get_active_backend() -> Optional[BaseBackend]:
    global _backend_instance, _active_backend_type
    backend_name = (
        type(_backend_instance).__name__
        if _backend_instance
        else 'None'
    )
    dbg_print(
        f"[BACKEND] get_active_backend() -- cached: "
        f"{backend_name} | "
        f"type: {_active_backend_type} | "
        f"cfg: {cfg.BACKEND_TYPE}"
    )
    if (
        _backend_instance is None
        or _active_backend_type != cfg.BACKEND_TYPE
    ):
        dbg_print(
            "[BACKEND] get_active_backend() -- "
            "MISMATCH, recreating..."
        )
        if _backend_instance is not None:
            dbg_print(
                "[BACKEND] Stopping old backend: "
                f"{type(_backend_instance).__name__}"
            )
            _backend_instance.stop()
        _backend_instance = create_backend()
    return _backend_instance


def shutdown_backend() -> None:
    global _backend_instance, _active_backend_type
    if _backend_instance is not None:
        _backend_instance.stop()
        _backend_instance = None
        _active_backend_type = None
