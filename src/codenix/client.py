from __future__ import annotations

from typing import Any

import httpx

from codenix.config import Config


class ClientError(RuntimeError):
    """API 返回非 2xx 或响应结构异常。"""

class ChatCompletionClient:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._http = httpx.Client(
            base_url=config.base_url,
            timeout=config.timeout,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            },
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> ChatCompletionClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self._config.model,
            "messages": messages,
            "temperature": self._config.temperature,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        response = self._http.post("/chat/completions", json=payload)
        if response.status_code >= 400:
            raise ClientError(
                f"API 错误 {response.status_code}: {response.text}"
            )

        data = response.json()
        return data
