"""Immutable configuration and statistics for XLSX exports.

XLSX 导出的不可变配置与统计。
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Self


@dataclass(frozen=True, slots=True)
class ExportConfig:
    """Immutable Excel export settings.

    不可变的 Excel 导出配置。
    """

    db: Path = field(default_factory=lambda: Path("data/emoji.db"))
    output: Path = field(default_factory=lambda: Path("data/emoji-catalog.xlsx"))
    pairs_per_row: int = 8
    per_sheet: int = 800
    image_size: int = 48


@dataclass(frozen=True, slots=True)
class ExportStats:
    """Immutable accumulated Excel export statistics.

    不可变的 Excel 导出累计统计。
    """

    total: int = 0
    embedded: int = 0
    converted: int = 0
    failed: int = 0
    sheets: int = 0

    def add_sheet(self) -> Self:
        """Return statistics with one additional catalog sheet.

        返回增加一个图册工作表后的统计。
        """
        return type(self)(
            total=self.total,
            embedded=self.embedded,
            converted=self.converted,
            failed=self.failed,
            sheets=self.sheets + 1,
        )

    def record_embedded(self, *, converted: bool) -> Self:
        """Return statistics containing one successful image export.

        返回记录一次成功图片导出后的统计。
        """
        return type(self)(
            total=self.total + 1,
            embedded=self.embedded + 1,
            converted=self.converted + int(converted),
            failed=self.failed,
            sheets=self.sheets,
        )

    def record_failure(self) -> Self:
        """Return statistics containing one failed image export.

        返回记录一次图片导出失败后的统计。
        """
        return type(self)(
            total=self.total + 1,
            embedded=self.embedded,
            converted=self.converted,
            failed=self.failed + 1,
            sheets=self.sheets,
        )


def validate_export_config(config: ExportConfig) -> str | None:
    """Return the first configuration error without mutating the settings.

    在不修改配置的前提下返回首个错误。
    """
    if config.pairs_per_row < 1:
        return "pairs-per-row must be positive"
    if config.per_sheet < 1:
        return "per-sheet must be positive"
    if config.image_size < 1:
        return "image-size must be positive"
    return None
