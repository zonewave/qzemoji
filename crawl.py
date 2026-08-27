"""Compatibility entry point for the src-layout crawler package.

src 布局爬虫包的兼容启动入口。
"""

from src import CrawlConfig, DownloadOutcome, download_gif, run
from src.crawler.cli import main

__all__ = ["CrawlConfig", "DownloadOutcome", "download_gif", "main", "run"]


if __name__ == "__main__":
    raise SystemExit(main())
