import sqlite3
from pathlib import Path
from typing import cast

from src.database import EmojiRepository

type ColumnInfo = tuple[int, str, str, int, str | None, int]


def test_repository_reuses_schema_and_preserves_upsert_semantics(tmp_path: Path) -> None:
    db = tmp_path / "emoji.db"
    with sqlite3.connect(db) as connection:
        _ = connection.executescript(
            """
            CREATE TABLE Emoji (
                eid INTEGER PRIMARY KEY,
                text VARCHAR NOT NULL,
                gif BLOB
            );
            CREATE TABLE Missing (
                eid INTEGER PRIMARY KEY,
                text VARCHAR NOT NULL
            );
            INSERT INTO Emoji (eid, text, gif) VALUES (1, 'saved emoji note', X'6F6C64');
            INSERT INTO Missing (eid, text) VALUES (2, 'saved missing note');
            """
        )

    with EmojiRepository(db) as repository:
        repository.upsert_emoji([(1, b"new"), (3, b"third")])
        repository.upsert_missing([(2,), (4,)])

        assert repository.load_skip() == {1, 2, 3, 4}

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
