from exceptions.expections import AuthenticationError
from typing import List, Tuple
from data.database import Database
import logging
import os

import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyOauthError

from data.util import parse_playlist_name


class SpotifyUtils:
    """Class to handle all use of the Spotify API including authentication for a single user."""

    def __init__(
        self,
        database: Database,
        username: str,
        cache_handler: spotipy.CacheHandler = None,
    ) -> None:
        """Init SpotifyUtils.

        Args:
            database (Database): The Database
            username (str): The user's username
            cache_handler (spotipy.CacheHandler, optional): An optional cache handler for Spotipy. Defaults to None.
        """
        self.database = database
        self.username = username
        self.auth = SpotifyOAuth(
            client_id=os.environ.get("SPOTIFY_CLIENT_ID", "none"),
            client_secret=os.environ.get("SPOTIFY_CLIENT_SECRET", "none"),
            redirect_uri=os.environ.get("BASE_URL", "https://discoveredweekly.com")
            + "/logged_in",
            scope="playlist-modify-private playlist-read-private user-library-read",
            cache_handler=cache_handler or database.get_cache_handler(self.username),
        )

    def auth_response(self, url: str) -> dict:
        """Parses the Spotify API response URL

        Args:
            url (str): The response URL

        Raises:
            AuthenticationError: if authentication fails at any point

        Returns:
            dict: Spotipy token info as dict
        """
        code = self.auth.parse_response_code(url)
        if not code:
            raise AuthenticationError("Authentication code not found in URL")
        try:
            return self.auth.get_access_token(code)
        except SpotifyOauthError as e:
            raise AuthenticationError(f"Invalid access token requested: {e}")

    def init_user(self, token_info: dict) -> Tuple[str, str, str]:
        """Initialises the user. Saves auth token and gets user info.

        Args:
            token_info (dict): Spotipy token info

        Returns:
            Tuple[str, str, str]: tuple of username, display name, discover weekly playlist id
        """
        logging.info("Access token successfully added. Getting user info")
        self.sp = spotipy.Spotify(token_info["access_token"])
        results = self.sp.current_user()
        logging.info(f"User results: {results}")
        username = results["id"]
        display_name = results["display_name"]

        cache_handler = self.database.get_cache_handler(username)
        cache_handler.save_token_to_cache(token_info)
        # Check if user has followed dw playlist
        dw_id = self.get_playlist_id("Discover Weekly")

        return username, display_name, dw_id

    def authenticate(self) -> bool:
        """Authenticates user in Spotipy via cached token.

        Returns:
            bool: whether authentication was successful
        """
        token_info = self.auth.cache_handler.get_cached_token()
        if token_info:
            try:
                token_info = self.auth.validate_token(token_info)
            except SpotifyOauthError as e:
                # TODO  Do correct error handling
                print("an error occured")
            access_token = token_info["access_token"]
            self.sp = spotipy.Spotify(access_token)
            return True
        else:
            logging.warning(f"No token found for user: {self.username}")
            return False

    def get_playlist_id(self, playlist_name: str) -> str:
        """Searches a specific playlist if a user's playlists.

        Args:
            playlist_name (str): The name to search for

        Returns:
            str: The spotify playlist id of the found playlist. Empty if not found.
        """
        playlist_id = ""
        i = 0
        while True:
            playlists = self.sp.current_user_playlists(offset=i * 50)["items"]
            for playlist in playlists:
                if playlist["name"] == playlist_name:
                    return playlist["id"]
            i += 1
            if not playlists:
                break
        return playlist_id

    def dw_tracks(self) -> Tuple[List[str], List[str], List[str]]:
        """Gets the tracks in the dw playlist.

        Returns:
            Tuple[List[str],List[str], List[str]]: tuple of lists of track ids, track names, and artists
        """
        dw_id = self.args.dw_id
        playlist_tracks = self.sp.user_playlist_tracks(
            user=self.args.username, playlist_id=dw_id
        )["items"]
        tracks = [x["track"] for x in playlist_tracks]
        ids, names, artists = [], [], []
        for track in tracks:
            ids.append(track["id"])
            names.append(track["name"])
            artists.append(", ".join(x["name"] for x in track["artists"]))
        return ids, names, artists

    def create_weekly(self, ids: List[str]) -> str:
        """Creates a playlist for the given week's songs.

        Args:
            ids (List[str]): List of song ids to be added to the playlist.

        Returns:
            str: The id of the newly created playlist
        """
        weekly_playlist_name = parse_playlist_name(self.args.weekly_name_template)
        # check if playlist exists already
        results = self.sp.user_playlist_create(
            user=self.args.username,
            name=weekly_playlist_name,
            public=False,
            description="Automatically created by Discovered Weekly.",
        )

        # find playlist id
        playlist_id = results["id"]

        # add tracks to playlist
        self.sp.user_playlist_add_tracks(
            user=self.args.username, playlist_id=playlist_id, tracks=ids
        )

        return playlist_id

    def create_full(self, ids: List[str]) -> str:
        """Creates the playlist to which all subsequent weeks' songs will be added.

        Args:
            ids (List[str]): List of song ids to be added to the playlist this week.

        Returns:
            str: The id of the newly created playlist
        """
        name = self.args.full_playlist_name
        full_playlist_id = self.args.full_playlist_id
        if not full_playlist_id:
            results = self.sp.user_playlist_create(
                user=self.args.username,
                name=name,
                public=False,
                description="Automatically created by Discovered Weekly.",
            )
            full_playlist_id = results["id"]

        self.sp.user_playlist_add_tracks(
            user=self.args.username, playlist_id=full_playlist_id, tracks=ids
        )
        return full_playlist_id
