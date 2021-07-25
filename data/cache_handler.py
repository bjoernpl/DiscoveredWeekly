import spotipy

from data.abs_database import AbsDatabase


class LossyCacheHandler(spotipy.CacheHandler):
    """CacheHandler implementation that does not save anything.

    This class is useful for initializing SpotifyUtils
    when the user is not known yet.
    """

    def get_cached_token(self) -> None:
        return None

    def save_token_to_cache(self, _) -> None:
        return None


class FirestoreCacheHandler(spotipy.CacheHandler):
    """CacheHandler implementation that saves spotify login token to the database."""

    def __init__(self, username: str, db: AbsDatabase) -> None:
        """Initialize FirestoreCacheHandler.

        Args:
            username (str): The user's username.
            db (AbsDatabase): The database instance to save to.
        """
        self.cacheHandler = spotipy.CacheFileHandler(username)
        self.username = username
        self.db = db

    def get_cached_token(self) -> dict:
        """Get the cached login token for the user from database.

        If there exists a local cached token, it is returned. Else
        the database is checked.
        Returns:
            dict: Spotify login token for this user.
        """
        cached_token = self.cacheHandler.get_cached_token()
        if not cached_token:
            token_ref = self.db.collection("tokens").document(self.username)
            token = token_ref.get()
            if token.exists:
                token_info = token.to_dict()
                return token_info
        return cached_token

    def save_token_to_cache(self, token_info: dict) -> None:
        """Saves spotify login token to local cache and database.

        Args:
            token_info (dict): Spotify login token for user.
        """
        self.cacheHandler.save_token_to_cache(token_info)
        self.db.collection("tokens").document(self.username).set(token_info)
