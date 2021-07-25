import os
from abc import ABC, abstractmethod
from typing import List
import logging

from firebase_admin import credentials, firestore, initialize_app

from data.user import User


class AbsDatabase(ABC):

    def __init__(self) -> None:
        self.test = (os.getenv('testing', 'False') == 'True')
        if self.test:
            from mockfirestore import MockFirestore
            self.db = MockFirestore()
            logging.info("Testing!")
        else:
            cred = credentials.ApplicationDefault()
            initialize_app(cred, {
                'projectId': os.getenv('FIREBASE_PROJECT_ID', 'None'),
            })
            self.db = firestore.Client()

    @abstractmethod
    def get_users(self,) -> List[User]:
        raise NotImplementedError

    @abstractmethod
    def add_user(self,username, display_name, dw_id):
        raise NotImplementedError

    @abstractmethod
    def update_user_playlist_ids(self,username, recent_id, full_id=None, dw_id=None):
        raise NotImplementedError

    @abstractmethod
    def get_cache_handler(self,username):
        raise NotImplementedError
