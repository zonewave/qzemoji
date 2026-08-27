"""Public crawling workflow API.

爬取工作流的公共 API。
"""

from .config import CrawlConfig
from .downloader import DownloadOutcome, download_gif
from .service import BatchResult, CrawlStats, classify_downloads, pending_batches, run

__all__ = [
    "BatchResult",
    "CrawlConfig",
    "CrawlStats",
    "DownloadOutcome",
    "classify_downloads",
    "download_gif",
    "pending_batches",
    "run",
]
