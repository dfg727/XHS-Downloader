from asyncio import CancelledError
from contextlib import suppress
from pathlib import Path

from aiosqlite import connect

from source.sitenav.module import BaseModule

__all__ = [
    "SudokuItem",
]


def _normalize_blanks(val):
    if isinstance(val, str):
        for char in (".", " ", "_"):
            val = val.replace(char, "0")
    return val


class SudokuItem(BaseModule):
    DATA_TABLE = (
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("name", "TEXT NOT NULL"),
        ("puzzle", "TEXT NOT NULL"),
        ("difficulty", "TEXT"),
        ("answer", "TEXT"),
        ("type", "TEXT NOT NULL"),
    )

    def __init__(self, db_folder_path: Path):
        super().__init__(db_folder_path)
        self.file = db_folder_path.joinpath("Sudoku.db")

    async def _connect_database(self):
        self.database = await connect(self.file)
        self.cursor = await self.database.cursor()
        await self.database.execute(
            f"""CREATE TABLE IF NOT EXISTS sudoku_item (
        {",".join(" ".join(i) for i in self.DATA_TABLE)}
        );"""
        )
        await self.database.commit()

    async def add(self, **kwargs) -> None:
        if "id" in kwargs:
            del kwargs["id"]

        valid_keys = [i[0] for i in self.DATA_TABLE if i[0] != "id" and i[0] in kwargs]
        columns = ", ".join(valid_keys)
        placeholders = ", ".join("?" for _ in valid_keys)
        values = tuple(
            _normalize_blanks(kwargs[k]) if k in ("puzzle", "answer") else kwargs[k]
            for k in valid_keys
        )

        await self.database.execute(
            f"""INSERT INTO sudoku_item (
        {columns}
        ) VALUES (
        {placeholders}
        );""",
            values,
        )
        await self.database.commit()

    async def select(self, id_: int | str):
        await self.cursor.execute("SELECT * FROM sudoku_item WHERE id = ?", (id_,))
        row = await self.cursor.fetchone()
        if row:
            columns = [col[0] for col in self.DATA_TABLE]
            return dict(zip(columns, row))
        return None

    async def delete(self, id_: int | str) -> None:
        await self.database.execute("DELETE FROM sudoku_item WHERE id = ?", (id_,))
        await self.database.commit()

    async def deletes(self, ids: list | tuple):
        if not ids:
            return
        placeholders = ", ".join("?" for _ in ids)
        await self.database.execute(
            f"DELETE FROM sudoku_item WHERE id IN ({placeholders})",
            tuple(ids),
        )
        await self.database.commit()

    async def all(self, difficulty: str = None, type_: str = None):
        query = "SELECT * FROM sudoku_item"
        params = []
        conditions = []
        if difficulty:
            conditions.append("LOWER(difficulty) = LOWER(?)")
            params.append(difficulty)
        if type_:
            conditions.append("LOWER(type) = LOWER(?)")
            params.append(type_)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        await self.cursor.execute(query, tuple(params))
        rows = await self.cursor.fetchall()

        columns = [col[0] for col in self.DATA_TABLE]
        dict_items = [dict(zip(columns, item)) for item in rows]

        return dict_items

    async def update(self, id_: int | str, **kwargs) -> None:
        valid_keys = [i[0] for i in self.DATA_TABLE if i[0] != "id" and i[0] in kwargs]
        if not valid_keys:
            return
        set_clause = ", ".join(f"{key} = ?" for key in valid_keys)
        values = list(
            _normalize_blanks(kwargs[k]) if k in ("puzzle", "answer") else kwargs[k]
            for k in valid_keys
        ) + [id_]
        await self.database.execute(f"UPDATE sudoku_item SET {set_clause} WHERE id = ?", values)
        await self.database.commit()
