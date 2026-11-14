from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from codenix import __version__
from codenix.agent import Agent, AgentError
from codenix.client import ClientError, ChatCompletionClient
from codenix.config import PROJECT_ROOT, Config, ConfigError
from codenix.history import ConversationHistory
from codenix.tools.registry import ToolContext, ToolError, ToolRegistry

SYSTEM_PROMPT_FILE = Path(__file__).resolve().parent / "prompts" / "system.md"
WORKSPACE_DIR = PROJECT_ROOT / "workspace"

HELP_TEXT = """可用命令：
  /help    显示帮助
  /clear   清空当前对话上下文（保留 system prompt）
  /model   显示当前模型
  /exit    退出（/quit 同义）"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codenix",
        description="基于 OpenAI 兼容 Chat Completions API 的终端 AI 编程助手。",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    prompt = args.prompt
    if prompt is not None and not prompt.strip():
        prompt = None

    if prompt is None and not sys.stdin.isatty():
        # 管道输入为空，且没有交互终端可用。
        parser.print_help()
        return 2

    try:
        config = Config.from_env()
    except ConfigError as exc:
        print(f"配置错误：{exc}", file=sys.stderr)
        return 2

    try:
        workspace = WORKSPACE_DIR.resolve()
        workspace.mkdir(parents=True, exist_ok=True)
        context = ToolContext(workspace=workspace, approve=_approve)
        registry = ToolRegistry.from_defaults(context)
    except (OSError, ToolError) as exc:
        print(f"工作目录或工具初始化失败：{exc}", file=sys.stderr)
        return 2

    client = ChatCompletionClient(config)
    agent = Agent(
        client=client,
        history=ConversationHistory(_load_system_prompt()),
        tool_registry=registry,
        on_tool_call=_show_tool_call,
        on_tool_result=_show_tool_result,
    )

    try:
        with client:
            return _run_interactive(agent, config)
    except ClientError as exc:
        print(f"API 错误：{exc}", file=sys.stderr)
        return 1

def _run_interactive(agent: Agent, config: Config) -> int:
    print(f"Codenix {__version__} | 模型：{config.model}")
    print("输入 /help 查看命令，/exit 退出。\n")

    while True:
        try:
            line = input("你 > ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        text = line.strip()
        if not text:
            continue

        if text.startswith("/"):
            if _handle_command(text, agent, config):
                return 0
            continue

        try:
            answer = agent.send(text)
        except ClientError as exc:
            print(f"API 错误：{exc}", file=sys.stderr)
            continue
        except AgentError as exc:
            print(f"Agent 错误：{exc}", file=sys.stderr)
            continue
        except KeyboardInterrupt:
            print("\n已取消本轮请求。", file=sys.stderr)
            continue

        print("\nCodenix：")
        print(answer)
        print()


def _handle_command(line: str, agent: Agent, config: Config) -> bool:
    """处理 Slash Command。返回 True 表示退出程序。"""

    command = line.split(maxsplit=1)[0].lower()

    if command in {"/exit", "/quit"}:
        print("再见。")
        return True
    if command == "/clear":
        agent.history.clear()
        print("已清空当前对话上下文。")
        return False
    if command == "/help":
        print(HELP_TEXT)
        return False
    if command == "/model":
        print(f"当前模型：{config.model}")
        return False

    print(f"未知命令：{command}。输入 /help 查看可用命令。")
    return False


def _approve(description: str) -> bool:
    """Shell 和写文件前的交互式审批。"""

    if not sys.stdin.isatty():
        print(
            f"\n[需要批准]\n{description}\n"
            "当前不是交互终端，已自动拒绝。",
            file=sys.stderr,
        )
        return False

    print(f"\n[需要批准]\n{description}")
    try:
        answer = input("允许执行？[y/N] > ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return answer in {"y", "yes"}


def _show_tool_call(name: str, arguments: dict[str, Any]) -> None:
    print(f"\n[工具调用] {name}")
    print(json.dumps(dict(arguments), ensure_ascii=False, indent=2))


def _show_tool_result(name: str, result: str) -> None:
    preview = result if len(result) <= 1500 else result[:1500] + "\n..."
    print(f"[工具结果] {name}\n{preview}\n")


def _load_system_prompt():
    from codenix.config import CONFIG_DIR
    system_prompt_path = CONFIG_DIR / "prompts" / "system.md"
    if system_prompt_path.exists():
        with open(system_prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    return "你是 Codenix，一个运行在 Linux 终端中的 AI 编程助手。"
