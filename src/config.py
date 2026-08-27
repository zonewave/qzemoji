"""Typed crawler configuration.

爬虫的类型化配置。
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CrawlConfig:
    """Immutable crawler runtime configuration.

    不可变的爬虫运行配置。
    """

    start: int = 0
    end: int = 1_001_001
    concurrency: int = 32
    timeout: float = 15
    db: Path = field(default_factory=lambda: Path("data/emoji.db"))


def validate_config(config: CrawlConfig) -> str | None:
    """Return the first validation error without mutating the configuration.

    在不修改配置的前提下返回首个校验错误。
    """
    if config.start < 0 or config.end < config.start:
        return "require 0 <= start <= end"
    if config.concurrency < 1:
        return "concurrency must be positive"
    if config.timeout <= 0:
        return "timeout must be positive"
    return None
