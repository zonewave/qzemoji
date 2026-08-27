"""Coordinate the resumable crawl workflow.

编排可断点续跑的爬取流程。
"""

import asyncio
import logging
from collections.abc import Iterator, Sequence
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from itertools import islice
from typing import Self

import aiohttp

from .config import CrawlConfig
from .database import EidRow, EmojiRepository, EmojiRow
from .downloader import DownloadOutcome, download_gif

log = logging.getLogger(__name__)


type DownloadResult = bytes | DownloadOutcome


@dataclass(frozen=True, slots=True)
class BatchResult:
    """Immutable classification of one downloaded batch.

    单个下载批次的不可变分类结果。
    """

    attempted: int
    emoji_rows: tuple[EmojiRow, ...]
    missing_rows: tuple[EidRow, ...]
    timed_out: int
    retryable_errors: int


@dataclass(frozen=True, slots=True)
class CrawlStats:
    """Immutable accumulated crawl statistics.

    不可变的累计爬取统计。
    """

    processed: int = 0
    new_found: int = 0
    new_missing: int = 0
    timed_out: int = 0
    retryable_errors: int = 0

    def merge(self, batch: BatchResult) -> Self:
        """Create updated statistics from a batch result.

        根据批次结果创建更新后的统计值。
        """
        return type(self)(
            processed=self.processed + batch.attempted,
            new_found=self.new_found + len(batch.emoji_rows),
            new_missing=self.new_missing + len(batch.missing_rows),
            timed_out=self.timed_out + batch.timed_out,
            retryable_errors=self.retryable_errors + batch.retryable_errors,
        )


def pending_batches(
    start: int,
    end: int,
    skip: AbstractSet[int],
    size: int,
) -> Iterator[tuple[int, ...]]:
    """Yield immutable batches of EIDs that still need processing.

    产出仍需处理的不可变 EID 批次。
    """
    pending = (eid for eid in range(start, end) if eid not in skip)
    while batch := tuple(islice(pending, size)):
        yield batch


def classify_downloads(
    eids: Sequence[int],
    results: Sequence[DownloadResult],
) -> BatchResult:
    """Purely classify download results into immutable persistence rows.

    以纯函数方式将下载结果分类为不可变的持久化记录。
    """
    emoji_rows: list[EmojiRow] = []
    missing_rows: list[EidRow] = []
    timed_out = 0
    retryable_errors = 0

    for eid, result in zip(eids, results, strict=True):
        if result is DownloadOutcome.TIMED_OUT:
            timed_out += 1
        elif result is DownloadOutcome.RETRY:
            retryable_errors += 1
        elif result is DownloadOutcome.MISSING:
            missing_rows.append((eid,))
        else:
            emoji_rows.append((eid, result))

    return BatchResult(
        attempted=len(eids),
        emoji_rows=tuple(emoji_rows),
        missing_rows=tuple(missing_rows),
        timed_out=timed_out,
        retryable_errors=retryable_errors,
    )


async def probe_batch(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    eids: Sequence[int],
) -> BatchResult:
    """Download one batch, leaving classification to a pure function.

    下载一个批次，并将分类交给纯函数处理。
    """
    results = await asyncio.gather(*(download_gif(session, eid, semaphore) for eid in eids))
    return classify_downloads(eids, results)


async def run(config: CrawlConfig) -> int:
    config.db.parent.mkdir(parents=True, exist_ok=True)
    with EmojiRepository(config.db) as repository:
        skip = repository.load_skip()

        total = config.end - config.start
        log.info(
            "range=[%s,%s) to_skip=%s",
            config.start,
            config.end,
            len(skip),
        )

        semaphore = asyncio.Semaphore(config.concurrency)
        connector = aiohttp.TCPConnector(
            limit=config.concurrency,
            limit_per_host=config.concurrency,
        )
        timeout = aiohttp.ClientTimeout(total=config.timeout)
        stats = CrawlStats()

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            for eids in pending_batches(config.start, config.end, skip, config.concurrency):
                batch = await probe_batch(session, semaphore, eids)
                repository.upsert_emoji(batch.emoji_rows)
                repository.upsert_missing(batch.missing_rows)
                stats = stats.merge(batch)
                if stats.processed % (config.concurrency * 200) == 0:
                    log.info(
                        "progress %s/%s new=%s missing=%s retry=%s timeout=%s",
                        stats.processed,
                        total,
                        stats.new_found,
                        stats.new_missing,
                        stats.retryable_errors,
                        stats.timed_out,
                    )

        log.info(
            "done: new_gif=%s new_missing=%s timed_out=%s retryable_errors=%s",
            stats.new_found,
            stats.new_missing,
            stats.timed_out,
            stats.retryable_errors,
        )
        return 0
