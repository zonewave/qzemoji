import sqlite3
from pathlib import Path
from typing import cast

from bitarray import frozenbitarray

from src.database import EmojiRepository

type ColumnInfo = tuple[int, str, str, int, str | None, int]


def test_repository_preserves_notes_and_uses_database_defaults(tmp_path: Path) -> None:
    db = tmp_path / "emoji.db"
    with sqlite3.connect(db) as connection:
        _ = connection.executescript(
            """
            CREATE TABLE Emoji (
                eid INTEGER PRIMARY KEY,
                text VARCHAR NOT NULL DEFAULT '',
                gif BLOB
            );
            CREATE TABLE Missing (
                eid INTEGER PRIMARY KEY,
                text VARCHAR NOT NULL DEFAULT ''
            );
            INSERT INTO Emoji (eid, text, gif) VALUES (1, 'saved emoji note', X'6F6C64');
            INSERT INTO Missing (eid, text) VALUES (2, 'saved missing note');
            """
        )

    with EmojiRepository(db) as repository:
        repository.upsert_emoji([(1, b"new"), (3, b"third")])
        repository.upsert_missing([(2,), (4,)])

        resolved = repository.load_skip(start=0, end=5)
        assert isinstance(resolved, frozenbitarray)
        assert resolved == frozenbitarray("01111")
        assert repository.load_skip(start=2, end=4) == frozenbitarray("11")

    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT eid, text, gif FROM Emoji ORDER BY eid").fetchall() == (
            [(1, "saved emoji note", b"new"), (3, "", b"third")]
        )
        assert connection.execute("SELECT eid, text FROM Missing ORDER BY eid").fetchall() == (
            [(2, "saved missing note"), (4, "")]
        )
        emoji_columns = cast(
            list[ColumnInfo], connection.execute('PRAGMA table_info("Emoji")').fetchall()
        )
        missing_columns = cast(
            list[ColumnInfo], connection.execute('PRAGMA table_info("Missing")').fetchall()
        )
        assert next(column[4] for column in emoji_columns if column[1] == "text") == "''"
        assert next(column[4] for column in missing_columns if column[1] == "text") == "''"
