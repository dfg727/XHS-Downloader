from asyncio import CancelledError
from contextlib import suppress
from pathlib import Path

from aiosqlite import connect

__all__ = [
    "BaseModule",
    "SiteItem",
]


class BaseModule:
    def __init__(self, db_folder_path: Path):
        self.file = db_folder_path.joinpath("**.db")
        self.database = None
        self.cursor = None

    async def _connect_database(self):
        pass

    async def __aenter__(self):
        await self._connect_database()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        with suppress(CancelledError):
            await self.cursor.close()
        await self.database.close()


class SiteItem(BaseModule):
    DATA_TABLE = (
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("pId", "INTEGER NOT NULL"),
        ("name", "TEXT NOT NULL"),
        ("desc", "TEXT"),
        ("uri", "TEXT"),
        ("isExpand", "INTEGER DEFAULT 0"),
        ("favicon", "TEXT"),
        ("status", "INTEGER DEFAULT 0"),
        ("category", "TEXT"),
        ("orderNum", "INTEGER DEFAULT 0"),
    )

    def __init__(self, db_folder_path: Path):
        super().__init__(db_folder_path)
        self.file = db_folder_path.joinpath("SiteNav.db")

    async def _connect_database(self):
        self.database = await connect(self.file)
        self.cursor = await self.database.cursor()
        await self.database.execute(
            f"""CREATE TABLE IF NOT EXISTS site_item (
        {",".join(" ".join(i) for i in self.DATA_TABLE)}
        );"""
        )
        await self.database.commit()

    async def add(self, **kwargs) -> None:
        # 排除 id 字段
        if "id" in kwargs:
            del kwargs["id"]

        # 仅插入 DATA_TABLE 中定义的且传入的字段
        valid_keys = [i[0] for i in self.DATA_TABLE if i[0] != "id" and i[0] in kwargs]
        columns = ", ".join(valid_keys)
        placeholders = ", ".join("?" for _ in valid_keys)
        values = tuple(kwargs[k] for k in valid_keys)

        await self.database.execute(
            f"""INSERT INTO site_item (
        {columns}
        ) VALUES (
        {placeholders}
        );""",
            values,
        )
        await self.database.commit()

    async def select(self, id_: str):
        await self.cursor.execute("SELECT ID FROM site_item WHERE ID=?", (id_,))
        return await self.cursor.fetchone()

    async def delete(self, id_: str) -> None:
        if id_:
            # 迭代获取所有需要删除的子孙节点 ID
            to_delete = [id_]
            index = 0
            while index < len(to_delete):
                current_id = to_delete[index]
                await self.cursor.execute("SELECT id FROM site_item WHERE pId = ?", (current_id,))
                rows = await self.cursor.fetchall()
                for row in rows:
                    to_delete.append(row[0])
                index += 1

            placeholders = ", ".join("?" for _ in to_delete)
            await self.database.execute(
                f"DELETE FROM site_item WHERE id IN ({placeholders})",
                tuple(to_delete),
            )
            await self.database.commit()

    async def deletes(self, ids: list | tuple):
        [await self.delete(i) for i in ids]

    async def all(self, category: str):
        await self.cursor.execute(
            "SELECT * FROM site_item WHERE LOWER(category) = LOWER(?) ORDER BY orderNum ASC",
            (category,),
        )
        rows = await self.cursor.fetchall()

        # 将元组转换为字典
        columns = [col[0] for col in SiteItem.DATA_TABLE]
        dict_items = [dict(zip(columns, item)) for item in rows]

        return dict_items

    async def update(self, id_: str, **kwargs) -> None:
        set_clause = ", ".join(f"{key} = ?" for key in kwargs)
        values = list(kwargs.values()) + [id_]
        await self.database.execute(f"UPDATE site_item SET {set_clause} WHERE id = ?", values)
        await self.database.commit()

    def __generate_values(self, data: dict) -> tuple:
        return tuple(data[i] for i, _ in self.DATA_TABLE if i in data)
