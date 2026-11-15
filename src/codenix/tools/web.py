from __future__ import annotations

from typing import Any, Protocol

import httpx

from codenix.tools.base import (
    ToolContext,
    ToolDenied,
    ToolError,
    optional_int,
    require_string,
)

class ToolConfig(Protocol):
    """工具配置接口，提供工具的默认参数。"""

    web_search_api_key: str | None

MAX_TIMEOUT = 30

def web_fetch(arguments: dict[str, Any], context: ToolContext) -> str:
    url = require_string(arguments, "url")
    timeout = optional_int(arguments, "timeout", MAX_TIMEOUT, minimum=1, maximum=MAX_TIMEOUT)

    if timeout <= 0:
        raise ToolError("timeout 必须大于 0")

    description = (
        f"URL：{url}\n"
        f"超时：{timeout:g} 秒"
    )
    if not context.request_approval(description):
        raise ToolDenied("用户未批准执行该 Web 请求")

    try:
        response = httpx.get(url, timeout=timeout)
        response.raise_for_status()
    except httpx.RequestError as exc:
        raise ToolError(f"请求失败：{exc}") from exc
    except httpx.HTTPStatusError as exc:
        raise ToolError(f"HTTP 错误 {exc.response.status_code}: {exc.response.text}") from exc

    return response.text

"""
def web_search(arguments: dict[str, Any], context: ToolContext) -> str:
    query = require_string(arguments, "query")
    count = optional_int(arguments, "count", 5, minimum=1, maximum=50)
    pass

"""
