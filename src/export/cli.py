"""Command-line interface for XLSX emoji catalog exports.

XLSX 表情图册导出的命令行接口。
"""

import argparse
import logging
from pathlib import Path
from typing import TypedDict, cast

from .config import EidFormat, ExportConfig, validate_export_config
from .xlsx import export_catalog

log = logging.getLogger(__name__)


class _ParsedArgs(TypedDict):
    db: Path
    output: Path
    pairs_per_row: int
    per_sheet: int
    image_size: int
    eid_format: EidFormat


def parse_args() -> ExportConfig:
    """Parse command-line values into an immutable export configuration.

    将命令行参数解析为不可变导出配置。
    """
    parser = argparse.ArgumentParser(description="Export Qzone emoji images to XLSX.")
    _ = parser.add_argument("--db", type=Path, default=Path("data/emoji.db"))
    _ = parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/emoji-catalog.xlsx"),
    )
    _ = parser.add_argument("--pairs-per-row", type=int, default=8)
    _ = parser.add_argument("--per-sheet", type=int, default=800)
    _ = parser.add_argument("--image-size", type=int, default=48)
    _ = parser.add_argument(
        "--eid-format",
        choices=("number", "message"),
        default="number",
        help="EID cell format: number or copyable chat message",
    )
    values = cast(_ParsedArgs, cast(object, vars(parser.parse_args())))
    config = ExportConfig(**values)
    if error := validate_export_config(config):
        parser.error(error)
    return config


def main() -> int:
    """Run the XLSX export command.

    运行 XLSX 导出命令。
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    config = parse_args()
    stats = export_catalog(config)
    log.info(
        "exported=%s converted=%s failed=%s sheets=%s output=%s",
        stats.embedded,
        stats.converted,
        stats.failed,
        stats.sheets,
        config.output,
    )
    return 0
