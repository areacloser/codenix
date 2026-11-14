from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from copy import deepcopy

Message = dict[str, Any]


@dataclass
class ConversationHistory:
    _system_prompt: str | None = None
    _messages: list[Message] = field(default_factory=list)

    @property
    def system_prompt(self) -> str | None:
        return self._system_prompt

    @property
    def messages(self) -> list[Message]:
        """返回内部列表的拷贝，以防止外部修改；系统提示词要和消息列表分开保存，以便在需要时可以重新加载系统提示词。"""
        messages = []
        if self._system_prompt:
            messages.append({"role": "system", "content": self._system_prompt})
        messages.extend(self._messages)
        return deepcopy(messages)

    def add_user(self, content: str) -> None:
        self._messages.append({"role": "user", "content": content})

    def add_assistant(self, message: Message) -> None:
        """追加模型返回的完整 assistant 消息（可能带 tool_calls）。"""
        self._messages.append(message)

    def add_tool_result(self, tool_call_id: str, content: str) -> None:
        self._messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content,
        })
