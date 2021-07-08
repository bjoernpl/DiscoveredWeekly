from abc import ABC, abstractmethod
from typing import List


class FirestoreBase(ABC):

    def __init__(self, db) -> None:
        self.db = db

    @abstractmethod
    def get_users() -> List[]:
        raise NotImplementedError

    @abstractmethod
    def add_user(username, display_name, dw_id):
        raise NotImplementedError

    @abstractmethod
    def update_user_playlist_ids(username, recent_id, full_id=None, dw_id=None):
        raise NotImplementedError

    @abstractmethod
    def get_cache_handler(username):
        raise NotImplementedError