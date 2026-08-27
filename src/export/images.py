"""Pure image preparation for XLSX embedding.

XLSX 嵌入前的纯图片处理。
"""

from dataclasses import dataclass
from io import BytesIO
from typing import Literal, TypedDict

from PIL import Image

type ImageSuffix = Literal["bmp", "gif", "jpg", "png"]

_IMAGE_SUFFIXES: dict[str, ImageSuffix] = {
    "BMP": "bmp",
    "GIF": "gif",
    "PNG": "png",
}


class ImageOptions(TypedDict):
    """Typed XlsxWriter image placement options.

    类型化的 XlsxWriter 图片布局选项。
    """

    image_data: BytesIO
    object_position: int
    x_offset: int
    y_offset: int
    x_scale: float
    y_scale: float
    description: str


@dataclass(frozen=True, slots=True)
class PreparedImage:
    """Immutable image data accepted by XlsxWriter.

    XlsxWriter 可接受的不可变图片数据。
    """

    data: bytes
    suffix: ImageSuffix
    width: int
    height: int
    converted: bool


def _as_png(image: Image.Image, width: int, height: int) -> PreparedImage:
    """Create a static PNG value from the current image frame.

    从当前图片帧创建静态 PNG 值。
    """
    output = BytesIO()
    image.convert("RGBA").save(output, format="PNG")
    return PreparedImage(output.getvalue(), "png", width, height, converted=True)


def prepare_image(payload: bytes) -> PreparedImage:
    """Preserve Excel-compatible images and convert other formats to PNG.

    保留 Excel 兼容图片，并将其他格式转换为 PNG。
    """
    with Image.open(BytesIO(payload)) as image:
        width, height = image.size
        image_format = image.format
        # XlsxWriter probes through byte 44, so normalize shorter valid images.
        # XlsxWriter 会探测到第 44 字节，因此需转换更短的合法图片。
        if image_format == "JPEG" and len(payload) >= 44:
            return PreparedImage(payload, "jpg", width, height, converted=False)
        if image_format in _IMAGE_SUFFIXES and len(payload) >= 44:
            return PreparedImage(
                payload,
                _IMAGE_SUFFIXES[image_format],
                width,
                height,
                converted=False,
            )

        image.seek(0)
        return _as_png(image, width, height)


def image_options(image: PreparedImage, cell_size: int, eid: int) -> ImageOptions:
    """Return centered options that fit an image into one cell.

    返回将图片居中缩放至单元格的选项。
    """
    scale = min(cell_size / image.width, cell_size / image.height)
    scaled_width = round(image.width * scale)
    scaled_height = round(image.height * scale)
    return {
        "image_data": BytesIO(image.data),
        "object_position": 1,
        "x_offset": max(0, (cell_size - scaled_width) // 2),
        "y_offset": max(0, (cell_size - scaled_height) // 2),
        "x_scale": scale,
        "y_scale": scale,
        "description": f"Qzone emoji {eid}",
    }
