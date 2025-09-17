# bot/storage.py
import aiosqlite
from pathlib import Path

DB_PATH = Path(__file__).parent / "bot.db"

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS auth (
  chat_id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  access TEXT NOT NULL,
  refresh TEXT NOT NULL
);
"""


class Storage:
    def __init__(self, db_path: str | Path = DB_PATH):
        self.db_path = str(db_path)

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(CREATE_SQL)
            await db.commit()

    async def upsert_tokens(self, chat_id: int, user_id: int, access: str, refresh: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO auth(chat_id,user_id,access,refresh) VALUES(?,?,?,?) "
                "ON CONFLICT(chat_id) DO UPDATE SET user_id=excluded.user_id, access=excluded.access, refresh=excluded.refresh",
                (chat_id, user_id, access, refresh),
            )
            await db.commit()

    async def get_auth(self, chat_id: int):
        """
       Получить user_id, access, refresh по chat_id.
       :param chat_id: Telegram chat_id
       :return: (user_id, access, refresh) или None
       """
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT user_id, access, refresh FROM auth WHERE chat_id=?", (chat_id,)) as cur:
                row = await cur.fetchone()
                if not row:
                    return None
                return int(row[0]), str(row[1]), str(row[2])

    async def update_access(self, chat_id: int, new_access: str) -> None:
        """
        Обновить access токен по chat_id.
        :param chat_id: Telegram chat_id
        :param new_access: новый access токен
        return: None
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE auth SET access=? WHERE chat_id=?", (new_access, chat_id))
            await db.commit()


store = Storage()
