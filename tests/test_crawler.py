import sqlite3
from pathlib import Path

import pytest

from src import crawler
from src.config import CrawlConfig
from src.crawler import CrawlStats, classify_downloads, pending_batches
from src.downloader import DownloadOutcome


@pytest.mark.parametrize("outcome", [DownloadOutcome.TIMED_OUT, DownloadOutcome.RETRY])
@pytest.mark.asyncio
async def test_retryable_outcome_is_not_recorded_as_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outcome: DownloadOutcome
) -> None:
    async def fail_temporarily(*_args: object, **_kwargs: object) -> DownloadOutcome:
        return outcome

    monkeypatch.setattr(crawler, "download_gif", fail_temporarily)
    db = tmp_path / "emoji.db"
    config = CrawlConfig(start=42, end=43, concurrency=1, timeout=1, db=db)

    _ = await crawler.run(config)

    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM Emoji").fetchone() == (0,)
        assert connection.execute("SELECT COUNT(*) FROM Missing").fetchone() == (0,)


def test_batch_transforms_are_immutable_values() -> None:
    batches = pending_batches(start=1, end=5, skip={2}, size=2)
    assert tuple(batches) == ((1, 3), (4,))

    batch = classify_downloads(
        (1, 2, 3, 4),
        (b"gif", DownloadOutcome.MISSING, DownloadOutcome.TIMED_OUT, DownloadOutcome.RETRY),
    )
    stats = CrawlStats().merge(batch)

    assert batch.emoji_rows == ((1, b"gif"),)
    assert batch.missing_rows == ((2,),)
    assert stats == CrawlStats(
        processed=4,
        new_found=1,
        new_missing=1,
        timed_out=1,
        retryable_errors=1,
    )
