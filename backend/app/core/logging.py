"""日志摘要工具。

LLM 与审计场景不得记录完整敏感内容,通过此处的 summarize_for_log 截断。
"""
from __future__ import annotations

import logging

_LOGGER_INITIALIZED = False


def init_logging() -> None:
    global _LOGGER_INITIALIZED
    if _LOGGER_INITIALIZED:
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    _LOGGER_INITIALIZED = True


def summarize_for_log(text: str | None, max_len: int = 200) -> str:
    """把文本截断到 max_len 字符,用于审计/日志摘要。"""
    if text is None:
        return ""
    text = str(text)
    if len(text) <= max_len:
        return text
    return text[:max_len] + f"...<truncated total={len(text)}>"
