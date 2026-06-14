import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ModelProfile:
    profile_key: str
    display_name: str
    think_open: Optional[str]
    think_close: Optional[str]
    reasoning_field: Optional[str]
    llama_cpp_thinking_kwarg: Optional[dict]
    ollama_uses_native_api: bool
    ollama_think_param: Optional[str]

    @property
    def supports_think_mode(self) -> bool:
        return bool(
            self.think_open is not None and self.think_close is not None
        )

    def get_thinking_kwargs(
        self, provider: str, think_mode: bool
    ) -> Optional[dict]:
        if provider == "ollama":
            if self.ollama_think_param:
                return {self.ollama_think_param: think_mode}
            return None
        if self.llama_cpp_thinking_kwarg:
            if think_mode:
                return dict(self.llama_cpp_thinking_kwarg)
            else:
                return {k: False for k in self.llama_cpp_thinking_kwarg}
        return None


PROFILES: dict[str, ModelProfile] = {
    "qwen": ModelProfile(
        profile_key="qwen",
        display_name="Qwen",
        think_open="<think>",
        think_close="</think>",
        reasoning_field="reasoning_content",
        llama_cpp_thinking_kwarg={"enable_thinking": True},
        ollama_uses_native_api=False,
        ollama_think_param="think",
    ),
    "gemma": ModelProfile(
        profile_key="gemma",
        display_name="Gemma",
        think_open="<think>",
        think_close="</think>",
        reasoning_field="thinking",
        llama_cpp_thinking_kwarg=None,
        ollama_uses_native_api=True,
        ollama_think_param="think",
    ),
}


def get_profile(profile_key: str) -> ModelProfile:
    return PROFILES.get(profile_key, PROFILES["qwen"])


def get_think_regex(profile: ModelProfile) -> Optional[re.Pattern]:
    if not profile.supports_think_mode:
        return None
    open_escaped = re.escape(profile.think_open)
    close_escaped = re.escape(profile.think_close)
    return re.compile(
        rf"{open_escaped}\s.*?\s{close_escaped}", re.DOTALL
    )
