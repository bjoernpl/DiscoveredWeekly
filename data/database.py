import logging
from datetime import datetime
from typing import Generator, List, Tuple

from data.abs_database import AbsDatabase
from data.cache_handler import FirestoreCacheHandler
from data.util import this_week
from data.user import User


class Database(AbsDatabase):

    def __init__(self) -> None:
        super().__init__()

    def get_users(self,) -> Generator[Tuple[str, User], None, None]:
        users = self.db.collection(u'users').get()
        return ((user.id, User.from_dict(user.to_dict())) for user in users)

    def user_exists(self, username) -> bool:
        doc = self.db.collection(u'users').document(username).get()
        return doc.exists

    def add_user(self, username, display_name, dw_id) -> Tuple[str, User]:
        user = User(
            date_created= datetime.now(),
            display_name= display_name,
            dw_id = dw_id
        )
        ref = self.db.collection(u'users').document(username)
        doc = ref.get()
        if not doc.exists:
            ref.set(user.to_dict())
            logging.info(f"Added user to firestore db: {username}")
        else:
            try:
                doc.get("dw_id")
            except KeyError:
                ref.set(user.to_dict(), merge=["dw_id"])
            logging.info(f"User {username} already exists")
        return doc.id, user

    def update_user_playlist_ids(self, username, recent_id, full_id=None, dw_id=None) -> None:
        if not full_id:
            ids = {
                "recent_weekly_id": recent_id,
                "last_cw" : this_week()
            }
        else:
            ids = {
                "recent_weekly_id": recent_id,
                "full_playlist_id": full_id,
                "dw_id": dw_id,
                "last_cw" : this_week()}
            
        ref = self.db.collection(u'users').document(username)
        ref.set(ids, merge=True)
        logging.info(f"Updated playlist ids for user: {username}")

    def save_tracks(self, ids, names, artists) -> None:
        if not self.test:
            batch = self.db.batch()
            for track_id, name, artist in zip(ids, names, artists):
                ref = self.db.collection(u"tracks").document(track_id)
                track = ref.get()
                if track.exists:
                    try:
                        count = track.get(u"count")
                        batch.update(ref, {
                            u"count" :  count + 1
                        })
                    except KeyError:
                        batch.set(ref, {
                            u"count" :  2
                        }, merge=[u"count"])
                else:
                    batch.set(ref, {
                        u"track_name": name,
                        u"artist": artist,
                        u"count" : 1
                    })
            batch.commit()


    def get_cache_handler(self, username) -> FirestoreCacheHandler:
        return FirestoreCacheHandler(username, self.db)
