"""Public API for the Qzone emoji crawler source package.

QQ 空间表情爬虫源码包的公共接口。
"""

from .crawler import CrawlConfig, DownloadOutcome, download_gif, run

__all__ = ["CrawlConfig", "DownloadOutcome", "download_gif", "run"]
