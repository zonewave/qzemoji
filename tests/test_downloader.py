import asyncio
from types import TracebackType
from typing import Self, cast

import aiohttp
import pytest

from src.downloader import DownloadOutcome, download_gif

pytestmark = pytest.mark.asyncio


async def test_download_timeout_has_distinct_outcome() -> None:
    class TimeoutRequest:
        async def __aenter__(self) -> None:
            raise TimeoutError

        async def __aexit__(
            self,
            _exc_type: type[BaseException] | None,
            _exc_value: BaseException | None,
            _traceback: TracebackType | None,
        ) -> None:
            return None

    class Session:
        def get(self, _url: str) -> TimeoutRequest:
            return TimeoutRequest()

    session = cast(aiohttp.ClientSession, cast(object, Session()))
    result = await download_gif(session, 42, asyncio.Semaphore(1))

    assert result is DownloadOutcome.TIMED_OUT


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (404, DownloadOutcome.MISSING),
        (429, DownloadOutcome.RETRY),
        (500, DownloadOutcome.RETRY),
    ],
)
async def test_only_404_is_missing(status: int, expected: DownloadOutcome) -> None:
    class Response:
        def __init__(self, response_status: int) -> None:
            self.status: int = response_status

        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(
            self,
            _exc_type: type[BaseException] | None,
            _exc_value: BaseException | None,
            _traceback: TracebackType | None,
        ) -> None:
            return None

        async def read(self) -> bytes:
            return b"gif"

    response = Response(status)

    class Session:
        def get(self, _url: str) -> Response:
            return response

    session = cast(aiohttp.ClientSession, cast(object, Session()))
    result = await download_gif(session, 42, asyncio.Semaphore(1))

    assert result is expected


async def test_network_error_is_retryable() -> None:
    class FailedRequest:
        async def __aenter__(self) -> None:
            raise aiohttp.ClientConnectionError

        async def __aexit__(
            self,
            _exc_type: type[BaseException] | None,
            _exc_value: BaseException | None,
            _traceback: TracebackType | None,
        ) -> None:
            return None

    class Session:
        def get(self, _url: str) -> FailedRequest:
            return FailedRequest()

    session = cast(aiohttp.ClientSession, cast(object, Session()))
    result = await download_gif(session, 42, asyncio.Semaphore(1))

    assert result is DownloadOutcome.RETRY
