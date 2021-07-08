import logging
import os

import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyOauthError

from data.util import parse_playlist_name


class SpotifyUtils:

    def __init__(self, database, username, cache_handler=None) -> None:
        self.database = database
        self.username = username
        self.auth = SpotifyOAuth(
            client_id=os.environ.get("SPOTIFY_CLIENT_ID", "none"), 
            client_secret=os.environ.get("SPOTIFY_CLIENT_SECRET", "none"), 
            redirect_uri=os.environ.get("BASE_URL", "https://discoveredweekly.com") + "/logged_in",
            scope="playlist-modify-private playlist-read-private user-library-read",
            cache_handler=cache_handler or database.get_cache_handler(self.username))

    
    def auth_response(self, url):
        access_token = ""
        code = self.auth.parse_response_code(url)
        if code:
            try:
                token_info = self.auth.get_access_token(code)
                access_token = token_info['access_token']
            except SpotifyOauthError as e:
                logging.warning(f"Invalid access token requested: {e}")
                
        if access_token:
            logging.info("Access token successfully added. Getting user info")
            self.sp = spotipy.Spotify(access_token)
            results = self.sp.current_user()
            logging.info(f"User results: {results}")
            username = results["id"]
            display_name = results["display_name"]

            cache_handler = self.database.get_cache_handler(username)
            cache_handler.save_token_to_cache(token_info)
            # Check if user has followed dw playlist
            dw_id = self.get_playlist_id("Discover Weekly")

            return username, display_name, dw_id
        else:
            return "test :D"


    def authenticate(self):
        
        token_info = self.auth.cache_handler.get_cached_token()
        if token_info:
            try:
                token_info = self.auth.validate_token(token_info)
            except SpotifyOauthError as e:
                #TODO  Do correct error handling
                print("an error occured")
            access_token = token_info['access_token']
            self.sp = spotipy.Spotify(access_token)
            return True
        else:
            logging.warning(f"No token found for user: {self.username}")
            return False

    def get_playlist_id(self, playlist_name):
        playlist_id = ''
        i=0
        while True:
            playlists = self.sp.current_user_playlists(offset=i*50)['items']
            for playlist in playlists:
                if playlist['name'] == playlist_name:
                    return playlist['id']
            i += 1
            if not playlists:
                break        
        return playlist_id

    def dw_tracks(self):
        dw_id = self.args.dw_id
        playlist_tracks = self.sp.user_playlist_tracks(
            user=self.args.username, 
            playlist_id=dw_id)["items"]
        tracks = [x["track"] for x in playlist_tracks]
        ids, names, artists  = [], [], []
        for track in tracks:
            ids.append(track["id"])
            names.append(track["name"])
            artists.append(", ".join(x["name"] for x in track["artists"]))
        return ids, names, artists


    def create_weekly(self, ids):
        weekly_playlist_name = parse_playlist_name(self.args.weekly_name_template)
        # check if playlist exists already
        results = self.sp.user_playlist_create(
            user=self.args.username, 
            name=weekly_playlist_name, 
            public=False, 
            description="Automatically created by Discovered Weekly.")

        # find playlist id
        playlist_id = results["id"]

        # add tracks to playlist
        self.sp.user_playlist_add_tracks(
            user=self.args.username, 
            playlist_id=playlist_id, 
            tracks=ids)

        return playlist_id
            

    def create_full(self, ids):
        name = self.args.full_playlist_name
        full_playlist_id = self.args.full_playlist_id
        if not full_playlist_id:
            results = self.sp.user_playlist_create(user=self.args.username, name=name, public=False, description="Automatically created by Discovered Weekly.")
            full_playlist_id = results["id"]

        self.sp.user_playlist_add_tracks(user=self.args.username, playlist_id=full_playlist_id, tracks=ids)
        return full_playlist_id
