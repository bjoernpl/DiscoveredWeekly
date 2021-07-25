import logging
from datetime import datetime
from typing import Generator, List, Tuple, Optional

from data.abs_database import AbsDatabase
from data.cache_handler import FirestoreCacheHandler
from data.util import this_week
from data.user import User


class Database(AbsDatabase):
    def __init__(self) -> None:
        super().__init__()

    def get_users(
        self,
    ) -> Generator[Tuple[str, User], None, None]:
        """Gets all users in database.

        Yields:
            Tuple[str, User]]: Tuple of user id and corresponding User object.
        """
        users = self.db.collection("users").stream()
        yield from ((user.id, User.from_dict(user.to_dict())) for user in users)

    def user_exists(self, username: str) -> bool:
        """Checks if a user exists in the database.

        Args:
            username (str): The username to check

        Returns:
            bool: If the user exists or not
        """
        doc = self.db.collection("users").document(username).get()
        return doc.exists

    def add_user(
        self, username: str, display_name: str, dw_id: str
    ) -> Tuple[str, User]:
        """Adds a user to the database.

        If the user already exists, it is checked if a dw_id was
        previously set.

        Args:
            username (str): The username of the user to add
            display_name (str): Their spotify display name
            dw_id (str): The spotify id of their Discover Weekly playlist

        Returns:
            Tuple[str, User]: Tuple of document id and User object
        """
        user = User(date_created=datetime.now(), display_name=display_name, dw_id=dw_id)
        ref = self.db.collection("users").document(username)
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

    def update_user_playlist_ids(
        self,
        username: str,
        recent_id: str,
        full_id: Optional[str] = None,
        dw_id: Optional[str] = None,
    ) -> None:
        """Updates a user's saved playlist ids.

        If this function is run for the first time for a user,
        the dw_id and full playlist id are also passed. Also updates
        the 'last_cw' field which indicates the last calender week
        where this user was updated.

        Args:
            username (str): The username of the user to update
            recent_id (str): The id of their recently created weekly playlist
            full_id (Optional[str], optional): Spotify playlist id to playlist containing all discoveries. Defaults to None.
            dw_id (Optional[str], optional): Spotify playlist id of the user's 'Discover Weekly' playlist. Defaults to None.
        """
        if not full_id:
            ids = {"recent_weekly_id": recent_id, "last_cw": this_week()}
        else:
            ids = {
                "recent_weekly_id": recent_id,
                "full_playlist_id": full_id,
                "dw_id": dw_id,
                "last_cw": this_week(),
            }

        ref = self.db.collection("users").document(username)
        ref.set(ids, merge=True)
        logging.info(f"Updated playlist ids for user: {username}")

    def save_tracks(self, ids: List[str], names: List[str], artists: List[str]) -> None:
        """Saves this week's tracks.

        Args:
            ids (List[str]): List of track ids
            names (List[str]): List of songs names
            artists (List[str]): List of artist names
        """
        if not self.test:
            batch = self.db.batch()
            for track_id, name, artist in zip(ids, names, artists):
                ref = self.db.collection("tracks").document(track_id)
                track = ref.get()
                if track.exists:
                    try:
                        count = track.get("count")
                        batch.update(ref, {"count": count + 1})
                    except KeyError:
                        batch.set(ref, {"count": 2}, merge=["count"])
                else:
                    batch.set(ref, {"track_name": name, "artist": artist, "count": 1})
            batch.commit()

    def get_cache_handler(self, username: str) -> FirestoreCacheHandler:
        """Returns a CacheHandler for this user.

        Args:
            username (str): The username of the user.

        Returns:
            FirestoreCacheHandler: CacheHandler for the Firestore database.
        """
        return FirestoreCacheHandler(username, self.db)
