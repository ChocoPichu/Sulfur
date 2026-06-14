from abc import ABC, abstractmethod
from typing import Generator, Optional, Any


class BaseBackend(ABC):
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    @abstractmethod
    def start(self) -> bool:
        ...

    @abstractmethod
    def stop(self) -> None:
        ...

    @abstractmethod
    def is_healthy(self) -> bool:
        ...

    @abstractmethod
    def chat_completion(
        self,
        messages,
        temperature: float,
        max_tokens: int,
        top_p: Optional[float],
        top_k: Optional[int],
        chat_template_kwargs: Optional[dict],
        model_name: str,
    ) -> Optional[str]:
        ...

    @abstractmethod
    def chat_completion_stream(
        self,
        messages,
        temperature: float,
        max_tokens: int,
        top_p: Optional[float],
        top_k: Optional[int],
        chat_template_kwargs: Optional[dict],
        model_name: str,
        tools: Optional[list] = None,
    ) -> Generator:
        ...

    @abstractmethod
    def list_models(self) -> list[str]:
        ...
