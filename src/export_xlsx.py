"""Export stored emoji images as a paginated Excel contact sheet.

将已存储的表情图片导出为分页 Excel 联系表。
"""

# XlsxWriter exposes dynamic, variadic APIs without a py.typed marker.
# XlsxWriter 暴露了未带 py.typed 标记的动态可变参数 API。
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import batched
from struct import error as StructError

import xlsxwriter
from PIL import UnidentifiedImageError
from xlsxwriter.exceptions import UndefinedImageSize, UnsupportedImageFormat
from xlsxwriter.format import Format
from xlsxwriter.worksheet import Worksheet

from .database import EmojiRepository
from .export_config import ExportConfig, ExportStats, validate_export_config
from .export_images import PreparedImage, image_options, prepare_image


@dataclass(frozen=True, slots=True)
class GridPosition:
    """Immutable cell coordinates for one EID/image pair.

    单个 EID/图片对的不可变单元格坐标。
    """

    row: int
    eid_column: int
    image_column: int


@dataclass(frozen=True, slots=True)
class ExportFailure:
    """Immutable image export failure.

    不可变的图片导出失败记录。
    """

    eid: int
    message: str


type ExportOutcome = PreparedImage | ExportFailure

_IMAGE_EXCEPTIONS: tuple[type[Exception], ...] = (
    OSError,
    StructError,
    UndefinedImageSize,
    UnidentifiedImageError,
    UnsupportedImageFormat,
    ValueError,
)


def grid_position(index: int, pairs_per_row: int) -> GridPosition:
    """Purely map a sheet-local index to grid coordinates.

    以纯函数方式将工作表内索引映射为网格坐标。
    """
    pair = index % pairs_per_row
    return GridPosition(
        row=1 + index // pairs_per_row,
        eid_column=pair * 2,
        image_column=pair * 2 + 1,
    )


def export_failure(eid: int, error: Exception) -> ExportFailure:
    """Purely convert an exception into an immutable failure value.

    以纯函数方式将异常转换为不可变失败值。
    """
    return ExportFailure(eid=eid, message=f"{type(error).__name__}: {error}")


def configure_catalog_sheet(
    worksheet: Worksheet,
    config: ExportConfig,
    header_format: Format,
) -> None:
    """Configure one repeated EID/image grid.

    配置一个重复的 EID/图片网格。
    """
    worksheet.hide_gridlines(2)
    worksheet.freeze_panes(1, 0)
    worksheet.set_zoom(85)
    _ = worksheet.set_row_pixels(0, 24)
    for pair in range(config.pairs_per_row):
        eid_column = pair * 2
        image_column = eid_column + 1
        _ = worksheet.set_column_pixels(eid_column, eid_column, 72)
        _ = worksheet.set_column_pixels(image_column, image_column, config.image_size + 4)
        _ = worksheet.write(0, eid_column, "EID", header_format)
        _ = worksheet.write(0, image_column, "Image", header_format)


def write_emoji(
    worksheet: Worksheet,
    position: GridPosition,
    eid: int,
    payload: bytes,
    image_size: int,
) -> ExportOutcome:
    """Write one grid entry and return its immutable outcome.

    写入一个网格项，并返回不可变结果。
    """
    _ = worksheet.set_row_pixels(position.row, image_size + 4)
    _ = worksheet.write_number(position.row, position.eid_column, eid)
    try:
        image = prepare_image(payload)
        _ = worksheet.insert_image(
            position.row,
            position.image_column,
            f"e{eid}.{image.suffix}",
            dict(image_options(image, image_size, eid)),
        )
        return image
    except _IMAGE_EXCEPTIONS as error:
        failure = export_failure(eid, error)
        _ = worksheet.write_string(position.row, position.image_column, "Decode error")
        return failure


def write_error_sheet(
    workbook: xlsxwriter.Workbook,
    failures: Sequence[ExportFailure],
) -> None:
    """Write image decoding failures to a dedicated worksheet.

    将图片解码失败记录写入独立工作表。
    """
    if not failures:
        return
    worksheet = workbook.add_worksheet("Errors")
    _ = worksheet.write_row(0, 0, ("EID", "Error"))
    _ = worksheet.set_column(0, 0, 12)
    _ = worksheet.set_column(1, 1, 80)
    for row, failure in enumerate(failures, start=1):
        _ = worksheet.write_number(row, 0, failure.eid)
        _ = worksheet.write_string(row, 1, failure.message)


def export_catalog(config: ExportConfig) -> ExportStats:
    """Stream database images into a multi-sheet XLSX contact sheet.

    将数据库图片流式写入多工作表 XLSX 联系表。
    """
    if error := validate_export_config(config):
        raise ValueError(error)

    config.output.parent.mkdir(parents=True, exist_ok=True)
    failures: list[ExportFailure] = []
    stats = ExportStats()

    with xlsxwriter.Workbook(config.output, {"constant_memory": True}) as workbook:
        workbook.set_properties(
            {
                "title": "Qzone Emoji Catalog",
                "subject": "EID and image contact sheets",
                "author": "qzone-emoji-crawler",
            }
        )
        header_format = workbook.add_format(
            {
                "bold": True,
                "align": "center",
                "valign": "vcenter",
                "bg_color": "#D9EAF7",
                "border": 1,
            }
        )

        with EmojiRepository(config.db) as repository:
            sheets = batched(repository.iter_emojis(), config.per_sheet)
            for sheet_number, rows in enumerate(sheets, start=1):
                stats = stats.add_sheet()
                worksheet = workbook.add_worksheet(f"Emoji {sheet_number:03d}")
                configure_catalog_sheet(worksheet, config, header_format)
                for index, (eid, payload) in enumerate(rows):
                    outcome = write_emoji(
                        worksheet,
                        grid_position(index, config.pairs_per_row),
                        eid,
                        payload,
                        config.image_size,
                    )
                    if isinstance(outcome, ExportFailure):
                        failures.append(outcome)
                        stats = stats.record_failure()
                    else:
                        stats = stats.record_embedded(converted=outcome.converted)

        write_error_sheet(workbook, failures)

    return stats
