"""Peewee persistence for crawl results.

使用 Peewee 持久化爬取结果。
"""

# Peewee builds queries dynamically and marks those APIs as unknown in its bundled stubs.
# Peewee 动态构建查询，其内置类型存根将这些 API 标记为 unknown。
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false

from collections.abc import Iterable, Sequence
from pathlib import Path
from types import TracebackType
from typing import Protocol, Self, cast, final

from peewee import (
    BlobField,
    DatabaseProxy,
    Default,
    IntegerField,
    Model,
    SqliteDatabase,
    TextField,
)
from playhouse.migrate import SqliteMigrator  # pyright: ignore[reportMissingTypeStubs]

database_proxy = DatabaseProxy()

type EmojiRow = tuple[int, bytes]
type EidRow = tuple[int]


class _ColumnMetadata(Protocol):
    """Typed subset of Peewee's SQLite column metadata.

    Peewee SQLite 列元数据的有类型子集。
    """

    name: str
    default: str | None


class _MigrationOperation(Protocol):
    """Typed interface implemented by delayed Peewee migrations.

    Peewee 延迟迁移操作实现的有类型接口。
    """

    def run(self) -> None:
        """Execute the delayed schema operation.

        执行延迟的表结构操作。
        """


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
        """Open the database, create tables, and ensure note defaults.

        打开数据库、创建数据表，并确保备注字段具有默认值。
        """
        _ = self.database.connect(reuse_if_open=True)
        self.database.create_tables([Emoji, Missing])
        self._ensure_text_defaults()
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

    def _ensure_text_defaults(self) -> None:
        """Set an empty database default without changing stored notes.

        将数据库默认值设为空字符串，不修改已存储的备注。
        """
        migrator = SqliteMigrator(self.database)
        for table in ("Emoji", "Missing"):
            columns = cast(Iterable[_ColumnMetadata], self.database.get_columns(table))
            text_column = next(column for column in columns if column.name == "text")
            if text_column.default == "''":
                continue

            with migrator.migration_context():
                if text_column.default is not None:
                    drop_default = cast(
                        _MigrationOperation,
                        cast(object, migrator.drop_column_default(table, "text")),
                    )
                    drop_default.run()
                add_default = cast(
                    _MigrationOperation,
                    cast(object, migrator.add_column_default(table, "text", "")),
                )
                add_default.run()

    def load_skip(self) -> set[int]:
        """Load EIDs already resolved as downloaded or missing.

        加载已经确认下载成功或资源缺失的 EID。
        """
        emoji_ids = cast(
            Iterable[EidRow],
            Emoji.select(Emoji.eid).where(Emoji.gif.is_null(False)).tuples(),
        )
        missing_ids = cast(Iterable[EidRow], Missing.select(Missing.eid).tuples())
        return {eid for (eid,) in emoji_ids} | {eid for (eid,) in missing_ids}

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
