"""Peewee persistence for crawl results.

使用 Peewee 持久化爬取结果。
"""

# Peewee builds queries dynamically and marks those APIs as unknown in its bundled stubs.
# Peewee 动态构建查询，其内置类型存根将这些 API 标记为 unknown。
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false

from collections.abc import Iterable, Sequence
from pathlib import Path
from types import TracebackType
from typing import Self, cast, final

from bitarray import frozenbitarray
from bitarray.util import zeros
from peewee import (
    BlobField,
    DatabaseProxy,
    Default,
    IntegerField,
    Model,
    SqliteDatabase,
    TextField,
)

database_proxy = DatabaseProxy()

type EmojiRow = tuple[int, bytes]
type EidRow = tuple[int]


class BaseModel(Model):
    """Bind crawler models through a runtime-configured database proxy.

    通过运行时配置的数据库代理绑定爬虫模型。
    """

    @final
    class Meta:
        database: DatabaseProxy = database_proxy


@final
class Emoji(BaseModel):
    eid: IntegerField[int] = IntegerField(primary_key=True)
    text: TextField[str] = TextField(constraints=[Default("''")])
    gif: BlobField[bytes | None] = BlobField(null=True)

    @final
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        table_name: str = "Emoji"


@final
class Missing(BaseModel):
    eid: IntegerField[int] = IntegerField(primary_key=True)
    text: TextField[str] = TextField(constraints=[Default("''")])

    @final
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        table_name: str = "Missing"


@final
class EmojiRepository:
    """Manage the crawler's Peewee connection and persistence operations.

    管理爬虫的 Peewee 连接及持久化操作。
    """

    def __init__(self, path: Path) -> None:
        """Configure a repository backed by the SQLite database at ``path``.

        配置一个由 ``path`` 指定的 SQLite 数据库仓储。
        """
        self.database: SqliteDatabase = SqliteDatabase(str(path))
        database_proxy.initialize(self.database)

    def __enter__(self) -> Self:
        """Open the database and create missing tables.

        打开数据库，并创建尚不存在的数据表。
        """
        _ = self.database.connect(reuse_if_open=True)
        self.database.create_tables([Emoji, Missing])
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_value: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        """Close the database when leaving the repository context.

        离开仓储上下文时关闭数据库。
        """
        if not self.database.is_closed():
            _ = self.database.close()

    def load_skip(self, start: int, end: int) -> frozenbitarray:
        """Load resolved EIDs in ``[start, end)`` as an immutable bitmap.

        将 ``[start, end)`` 内已下载或已确认缺失的 EID 加载为不可变位图。
        """
        resolved = zeros(end - start)
        queries = (
            Emoji.select(Emoji.eid).where(
                Emoji.gif.is_null(False),
                Emoji.eid >= start,
                Emoji.eid < end,
            ),
            Missing.select(Missing.eid).where(
                Missing.eid >= start,
                Missing.eid < end,
            ),
        )
        for query in queries:
            # iterator() prevents Peewee from retaining every selected row.
            # iterator() 避免 Peewee 缓存所有已读取的行。
            rows = cast(Iterable[EidRow], query.tuples().iterator())
            for (eid,) in rows:
                resolved[eid - start] = True
        return frozenbitarray(resolved)

    def upsert_emoji(self, rows: Sequence[EmojiRow]) -> None:
        """Insert emoji rows and replace GIFs on EID conflicts.

        插入表情记录；EID 冲突时仅替换 GIF 数据。
        """
        if not rows:
            return
        query = Emoji.insert_many(rows, fields=[Emoji.eid, Emoji.gif]).on_conflict(
            conflict_target=[Emoji.eid],
            preserve=[Emoji.gif],
        )
        _ = query.execute()

    def upsert_missing(self, rows: Sequence[EidRow]) -> None:
        """Insert missing EIDs while preserving existing records.

        插入缺失 EID，并在冲突时保留已有记录。
        """
        if not rows:
            return
        query = Missing.insert_many(rows, fields=[Missing.eid]).on_conflict_ignore()
        _ = query.execute()
