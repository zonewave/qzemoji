from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from PIL import Image

from src.database import EmojiRepository
from src.export_config import ExportConfig
from src.export_xlsx import export_catalog


def image_bytes(image_format: str, color: str) -> bytes:
    """Create a small in-memory image fixture.

    创建小型内存图片测试数据。
    """
    output = BytesIO()
    Image.new("RGBA", (4, 4), color).save(output, format=image_format)
    return output.getvalue()


def test_export_catalog_embeds_images_and_reports_invalid_rows(tmp_path: Path) -> None:
    db = tmp_path / "emoji.db"
    output = tmp_path / "emoji-catalog.xlsx"
    with EmojiRepository(db) as repository:
        repository.upsert_emoji(
            [
                (1, image_bytes("PNG", "red")),
                (2, image_bytes("GIF", "blue")),
                (3, b"not an image"),
            ]
        )

    stats = export_catalog(
        ExportConfig(
            db=db,
            output=output,
            pairs_per_row=2,
            per_sheet=2,
            image_size=24,
        )
    )

    assert stats.total == 3
    assert stats.embedded == 2
    assert stats.failed == 1
    assert stats.sheets == 2
    assert not hasattr(stats, "__dict__")
    with ZipFile(output) as archive:
        names = archive.namelist()
        assert sum(name.startswith("xl/media/") for name in names) == 2
        assert "xl/worksheets/sheet3.xml" in names
