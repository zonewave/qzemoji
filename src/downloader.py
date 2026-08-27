"""Download individual Qzone emoji GIFs.

下载单个 QQ 空间表情 GIF。
"""

import asyncio
from enum import Enum, auto

import aiohttp

EMOJI_URL = "http://qzonestyle.gtimg.cn/qzone/em/e{eid}.gif"


class DownloadOutcome(Enum):
    MISSING = auto()
    TIMED_OUT = auto()
    RETRY = auto()


async def download_gif(
    session: aiohttp.ClientSession, eid: int, semaphore: asyncio.Semaphore
) -> bytes | DownloadOutcome:
    """Download one GIF, treating only HTTP 404 as permanently missing."""
    async with semaphore:
        try:
            async with session.get(EMOJI_URL.format(eid=eid)) as response:
                if response.status == 404:
                    return DownloadOutcome.MISSING
                if response.status != 200:
                    return DownloadOutcome.RETRY
                return await response.read()
        except TimeoutError:
            return DownloadOutcome.TIMED_OUT
        except aiohttp.ClientError:
            return DownloadOutcome.RETRY
