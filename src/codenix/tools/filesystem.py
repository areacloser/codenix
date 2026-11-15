from __future__ import annotations

from typing import Any
from pathlib import Path

from codenix.tools.base import (
    ToolContext,
    ToolDenied,
    ToolError,
    optional_int,
    require_string,
    optional_bool,
    optional_string,
)

MAX_READ_BYTES = 2 * 1024 * 1024  # 2 MB
MAX_LINE_CHARS = 200
MAX_READ_LINES = 2000
MAX_LIST_ENTRIES = 1000

IGNORED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
}


def read_file(arguments: dict[str, Any], context: ToolContext) -> str:
    path = context.resolve_path(require_string(arguments, "path"))
    relative = context.relative_path(path)

    if not path.exists():
        raise ToolError(f"文件不存在：{relative}")
    if not path.is_file():
        raise ToolError(f"不是普通文件：{relative}")

    try:
        if path.stat().st_size > MAX_READ_BYTES:
            raise ToolError(f"文件过大，最多读取 {MAX_READ_BYTES} 字节")
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise ToolError(f"读取文件失败：{exc}") from exc

    if "\x00" in text:
        raise ToolError("疑似二进制文件，拒绝读取")

    lines = text.splitlines()
    total = len(lines)
    start = optional_int(arguments, "start_line", 1, minimum=1)
    end = _get_end_line(arguments, start, total)

    if total == 0:
        return f"{relative}（空文件）"
    if start > total:
        return f"{relative} 只有 {total} 行，start_line={start} 超出范围"

    end = min(end, total, start + MAX_READ_LINES - 1)
    numbered = []
    for number in range(start, end + 1):
        line = lines[number - 1]
        if len(line) > MAX_LINE_CHARS:
            line = line[:MAX_LINE_CHARS] + " ..."
        numbered.append(f"{number:>6}\t{line}")

    header = f"{relative}（第 {start}-{end} 行，共 {total} 行）"
    if end < total:
        header += "；内容已截断"
    return "\n".join([header, *numbered])


def write_file(arguments: dict[str, Any], context: ToolContext) -> str:
    path = context.resolve_path(require_string(arguments, "path"))
    content = arguments.get("content")
    if not isinstance(content, str):
        raise ToolError("参数 content 必须是字符串")

    relative = context.relative_path(path)
    if path.exists() and path.is_dir():
        raise ToolError(f"目标是一个目录：{relative}")

    description = f"写入文件：{relative}\n字符数：{len(content)}"
    if not context.request_approval(description):
        raise ToolDenied("用户未批准写入文件")

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise ToolError(f"写入文件失败：{exc}") from exc

    return f"已写入 {relative}（{len(content)} 字符）"


def list_files(arguments: dict[str, Any], context: ToolContext) -> str:
    path = context.resolve_path(optional_string(arguments, "path", "."))
    if not path.exists():
        raise ToolError(f"路径不存在：{context.relative_path(path)}")

    if path.is_file():
        return f"路径：{context.relative_path(path)}\n{context.relative_path(path)}"

    recursive = optional_bool(arguments, "recursive", False)
    max_depth = optional_int(
        arguments, "max_depth", 2, minimum=1, maximum=10
    )
    entries = _list_entries(path, recursive=recursive, max_depth=max_depth)
    total = len(entries)
    truncated = total > MAX_LIST_ENTRIES
    visible = entries[:MAX_LIST_ENTRIES]

    header = f"目录：{context.relative_path(path)}（{total} 项）"
    if truncated:
        header += f"，仅显示前 {MAX_LIST_ENTRIES} 项"
    if not visible:
        return header + "\n(空)"

    result = [header, *visible]
    if truncated:
        result.append("...（列表已截断）")
    return "\n".join(result)


def get_file_info(arguments: dict[str, Any], context: ToolContext) -> str:
    path = context.resolve_path(require_string(arguments, "path"))
    relative = context.relative_path(path)

    if not path.exists():
        raise ToolError(f"路径不存在：{relative}")

    info = {
        "路径": relative,
        "类型": "目录" if path.is_dir() else "文件",
        "大小": f"{path.stat().st_size} 字节" if path.is_file() else "-",
        "最后修改时间": path.stat().st_mtime,
    }

    return "\n".join(f"{key}: {value}" for key, value in info.items())


def delete_file(arguments: dict[str, Any], context: ToolContext) -> str:
    path = context.resolve_path(require_string(arguments, "path"))
    relative = context.relative_path(path)

    if not path.exists():
        raise ToolError(f"路径不存在：{relative}")

    description = f"删除路径：{relative}"
    if not context.request_approval(description):
        raise ToolDenied("用户未批准删除文件或目录")

    try:
        if path.is_dir():
            for child in path.iterdir():
                if child.is_dir():
                    raise ToolError(f"目录不为空：{context.relative_path(child)}")
            path.rmdir()
        else:
            path.unlink()
    except OSError as exc:
        raise ToolError(f"删除失败：{exc}") from exc

    return f"已删除 {relative}"


def _get_end_line(
    arguments: dict[str, Any],
    start: int,
    total: int,
) -> int:
    raw = arguments.get("end_line")
    if raw is None:
        return max(total, start)
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise ToolError("参数 end_line 必须是整数")
    if raw < start:
        raise ToolError("end_line 不能小于 start_line")
    return raw


def _list_entries(
    root: Path,
    *,
    recursive: bool,
    max_depth: int,
) -> list[str]:
    entries: list[str] = []

    if not recursive:
        for entry in sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name)):
            if entry.is_dir() and entry.name in IGNORED_DIRS:
                continue
            suffix = "/" if entry.is_dir() else ""
            entries.append(entry.name + suffix)
        return entries

    for dirpath, dirnames, filenames in root.walk(follow_symlinks=False):
        current = Path(dirpath)
        relative_dir = current.relative_to(root)
        depth = len(relative_dir.parts)

        dirnames[:] = sorted(
            name
            for name in dirnames
            if name not in IGNORED_DIRS
            and not (current / name).is_symlink()
        )
        if depth >= max_depth:
            dirnames[:] = []
            continue

        for name in dirnames:
            entries.append((relative_dir / name).as_posix() + "/")
        for name in sorted(filenames):
            entries.append((relative_dir / name).as_posix())

    entries.sort()
    return entries
