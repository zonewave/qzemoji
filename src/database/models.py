"""Peewee models and persistence row types.

Peewee 模型与持久化行类型。
"""

# Peewee leaves the SQL default factory value untyped in its bundled annotations.
# Peewee 在内置注解中未标注 SQL 默认值工厂的参数类型。
# pyright: reportUnknownVariableType=false

from typing import final

from peewee import (
    BlobField,
    DatabaseProxy,
    Default,
    IntegerField,
    Model,
    TextField,
)

database_proxy = DatabaseProxy()

type EmojiRow = tuple[int, bytes]
type EidRow = tuple[int]


class BaseModel(Model):
    """Bind models through a runtime-configured database proxy.

    通过运行时配置的数据库代理绑定模型。
    """

    @final
    class Meta:
        database: DatabaseProxy = database_proxy


@final
class Emoji(BaseModel):
    """Downloaded emoji image record.

    已下载的表情图片记录。
    """

    eid: IntegerField[int] = IntegerField(primary_key=True)
    text: TextField[str] = TextField(constraints=[Default("''")])
    gif: BlobField[bytes | None] = BlobField(null=True)

    @final
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        table_name: str = "Emoji"


@final
class Missing(BaseModel):
    """Permanently missing emoji EID record.

    已确认永久缺失的表情 EID 记录。
    """

    eid: IntegerField[int] = IntegerField(primary_key=True)
    text: TextField[str] = TextField(constraints=[Default("''")])

    @final
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        table_name: str = "Missing"
