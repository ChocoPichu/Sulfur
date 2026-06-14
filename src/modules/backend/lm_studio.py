import requests
from typing import Generator, Optional

from .base import BaseBackend
from .protocol_openai import OpenAIProtocol, LLMRequest, LLMEvent
import src.modules.configurations as cfg
from src.modules.configurations import dbg_print

DEFAULT_LM_STUDIO_URL = "http://127.0.0.1:1234"


class LMStudioBackend(BaseBackend):
    def __init__(self, base_url: str = DEFAULT_LM_STUDIO_URL):
        super().__init__(base_url)
        self._protocol = OpenAIProtocol(base_url=self.base_url)
        self._num_ctx = getattr(cfg, "NUM_CTX", 4096)
        self._logged_ctx = False

    def start(self) -> bool:
        dbg_print(f"\n[LM STUDIO] Connecting to {self.base_url}...")
        healthy = self.is_healthy()
        if healthy:
            models = self.list_models()
            dbg_print(
                f"[LM STUDIO] Connected -- "
                f"{len(models)} model(s) available"
            )
        else:
            dbg_print(
                f"[LM STUDIO] Connection failed -- "
                f"is LM Studio running?"
            )
        return healthy

    def stop(self) -> None:
        pass

    def is_healthy(self) -> bool:
        return self._protocol.check_health()

    def _build_request(
        self,
        messages,
        temperature,
        max_tokens,
        top_p,
        top_k,
        chat_template_kwargs,
        model_name,
        tools=None,
    ) -> LLMRequest:
        if not self._logged_ctx:
            dbg_print(
                f"[LM STUDIO] Request -- Model: {model_name} | "
                f"Context: {self._num_ctx} | "
                f"Temperature: {getattr(cfg, 'TEMPERATURE', 0.7)}"
            )
            self._logged_ctx = True
        return LLMRequest(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            top_k=top_k,
            chat_template_kwargs=chat_template_kwargs,
            model_name=model_name,
            tools=tools,
            num_ctx=self._num_ctx,
        )

    def chat_completion(
        self,
        messages,
        temperature,
        max_tokens,
        top_p,
        top_k,
        chat_template_kwargs,
        model_name,
    ) -> Optional[str]:
        request = self._build_request(
            messages, temperature, max_tokens, top_p, top_k,
            chat_template_kwargs, model_name,
        )
        return self._protocol.complete(request)

    def chat_completion_stream(
        self,
        messages,
        temperature,
        max_tokens,
        top_p,
        top_k,
        chat_template_kwargs,
        model_name,
        tools=None,
    ) -> Generator:
        request = self._build_request(
            messages, temperature, max_tokens, top_p, top_k,
            chat_template_kwargs, model_name, tools,
        )
        yield from self._protocol.stream(request)

    def list_models(self) -> list[str]:
        return self._protocol.list_models()
