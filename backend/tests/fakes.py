"""Offline stand-ins for LangChain chat models."""

from typing import Any, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field


class FakeChatModel(BaseChatModel):
    """Returns queued AIMessages (or raises ``error``) and records every call."""

    responses: List[AIMessage] = Field(default_factory=list)
    error: Optional[Any] = None
    calls: List[dict] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "fake-offline"

    def _generate(self, messages: List[BaseMessage], stop=None, run_manager=None, **kwargs: Any) -> ChatResult:
        self.calls.append({"messages": messages, "kwargs": kwargs})
        if self.error is not None:
            raise self.error
        return ChatResult(generations=[ChatGeneration(message=self.responses.pop(0))])
