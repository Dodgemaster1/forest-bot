from dataclasses import dataclass
from pathlib import Path

from tinydb import Query, TinyDB


@dataclass
class User:
    name: str
    user_id: int
    files: list[str]


class DB:
    def __init__(self, users_db_path: Path = Path("data") / "users.json") -> None:
        users_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = TinyDB(users_db_path)

    def add_user(self, name: str, user_id: int) -> None:
        self.db.insert({"name": name, "user_id": user_id, "files": []})

    def get_user_by_id(self, user_id: int) -> User | None:
        user = Query()
        result = self.db.search(user.user_id == user_id)
        if result:
            return User(**result[0])
        return None

    def get_user_by_document(self, filename: str) -> User | None:
        user = Query()
        result = self.db.search(user.files.any([filename]))
        if result:
            return User(**result[0])
        return None

    def save_document(self, user_id: int, filename: str) -> None:
        user = Query()
        self.db.update(lambda doc: doc["files"].append(filename), user.user_id == user_id)
