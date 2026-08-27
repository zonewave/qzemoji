"""Command-line interface for the crawler.

爬虫的命令行接口。
"""

import argparse
import asyncio
import logging
from pathlib import Path
from typing import TypedDict, cast

from .config import CrawlConfig, validate_config
from .crawler import run


class _ParsedArgs(TypedDict):
    start: int
    end: int
    concurrency: int
    timeout: float
    db: Path


def parse_args() -> CrawlConfig:
    parser = argparse.ArgumentParser(description="Crawl Qzone emoji GIFs into SQLite.")
    _ = parser.add_argument("--start", type=int, default=0, help="first eid (inclusive)")
    _ = parser.add_argument("--end", type=int, default=1_001_001, help="last eid (exclusive)")
    _ = parser.add_argument("--concurrency", type=int, default=32, help="concurrent requests")
    _ = parser.add_argument("--timeout", type=float, default=15, help="request timeout in seconds")
    _ = parser.add_argument("--db", type=Path, default=Path("data/emoji.db"))
    values = cast(_ParsedArgs, cast(object, vars(parser.parse_args())))
    config = CrawlConfig(**values)
    if error := validate_config(config):
        parser.error(error)
    return config


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    return asyncio.run(run(parse_args()))
