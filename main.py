import os

import logging
from typing import NamedTuple
from flask import Flask, render_template, request, redirect
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from datetime import datetime
import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyOauthError
from collections import namedtuple

class LossyCacheHandler(spotipy.CacheHandler):
    def get_cached_token(self):
        return None

    def save_token_to_cache(self, token_info):
        return None

class FirestoreCacheHandler(spotipy.CacheHandler):
    def __init__(self, username, db) -> None:
        self.cacheHandler = spotipy.CacheFileHandler(username)
        self.username = username
        self.db = db

    def get_cached_token(self):
        cached_token = self.cacheHandler.get_cached_token()
        if not cached_token:
            token_ref = self.db.collection("tokens").document(self.username)
            if token_ref.exists:
                token_info = token_ref.get().to_dict()
                return token_info
        return None
            
    def save_token_to_cache(self, token_info):
        self.cacheHandler.save_token_to_cache(token_info)
        self.db.collection("tokens").document(self.username).set(token_info)
    

# Use the application default credentials for firebase admin
cred = credentials.ApplicationDefault()
firebase_admin.initialize_app(cred, {
  'projectId': "discovered-weekly-316016",
})
db = firestore.client()

# Base spotify OAuth
auth = SpotifyOAuth(
        client_id=os.environ.get("SPOTIFY_CLIENT_ID", "none"), 
        client_secret=os.environ.get("SPOTIFY_CLIENT_SECRET", "none"), 
        redirect_uri="https://pluester.dev/logged_in",
        scope="playlist-modify-private playlist-read-private user-library-read",
        cache_handler=LossyCacheHandler())

# Flask app
app = Flask(__name__)

@app.route("/")
def main():
    """ Main page
    """
    auth_url = auth.get_authorize_url()
    logging.debug(f"Authentication URL for user is: {auth_url}")
    return render_template("main.html", auth_url=auth_url)

@app.route("/logged_in")
def logged_in():
    """ Response to successful login authorization. URL here contains auth token
    """
    access_token = ""
    url = request.url
    code = auth.parse_response_code(url)
    if code:
        try:
            token_info = auth.get_access_token(code)
        except SpotifyOauthError as e:
            logging.warning(f"Invalid access token requested: {e}")
        finally:
            access_token = token_info['access_token']

    if access_token:
        logging.info("Access token successfully added. Getting user info")
        sp = spotipy.Spotify(access_token)
        results = sp.current_user()
        logging.info(f"User results: {results}")
        username = results["id"]
        display_name = results["display_name"]
        add_user(username, display_name)

        cache_handler = FirestoreCacheHandler(username)
        cache_handler.save_token_to_cache(token_info)
        
        return f"You have successfully logged in as {display_name} ({username}). Your 'Discover Weekly' playlist will be copied every monday at 7:00 CET"

    else:
        return "test :D"

@app.route("/error")
def error():
    pass


def get_users():
    users = db.collection(u'users').get()
    return (user.id for user in users)
    
def add_user(username, display_name):
    user = {
        "date_created" : datetime.now(),
        "display_name": display_name
    }
    ref = db.collection(u'users').document(username)
    if not ref.get().exists:
        ref.set(user)
        logging.info(f"Added user to firestore db: {username}")
    else:
        logging.info(f"User {username} already exists")


@app.route("/save_playlists", methods = ['POST'])
def save_playlists():
    code = request.headers.get("passcode", "placeholder")
    if code == os.environ.get("SAVE_PLAYLISTS_CODE"):
        logging.info("Beginning playlist extraction.")
        for user in get_users():
            cache_handler = FirestoreCacheHandler(user)
            auth = SpotifyOAuth(
                client_id=os.environ.get("SPOTIFY_CLIENT_ID", "none"), 
                client_secret=os.environ.get("SPOTIFY_CLIENT_SECRET", "none"), 
                redirect_uri="https://pluester.dev/logged_in",
                scope="playlist-modify-private playlist-read-private user-library-read",
                cache_handler=cache_handler)
            token_info = auth.cache_handler.get_cached_token()
            if token_info:
                try:
                    token_info = auth.validate_token(token_info)
                except SpotifyOauthError as e:
                    #TODO  Do correct error handling
                    print("an error occured")
                access_token = token_info['access_token']
                sp = spotipy.Spotify(access_token)
                run_for_user(sp, user)
            else:
                logging.warning(f"No token found for user: {user}")
                continue
        return "Success"
    else:
        return "You should not be here. Shoo"


def parse_playlist_name(name):
    today = datetime.today()
    year, week, _ = today.isocalendar()
    name = name.replace("{week_of_year}", f"{week}")
    name = name.replace("{year}", f"{year}")
    name = name.replace("{month}", f"{today.month}")
    return name

def get_playlist_id(sp, playlist_name):
    playlist_id = ''
    i=0
    while True:
        playlists = sp.current_user_playlists(offset=i*50)['items']
        for playlist in playlists:
            if playlist['name'] == playlist_name:
                playlist_id = playlist['id']
                break
        i += 1
        if not playlists:
            break        
    return playlist_id

def dw_tracks(sp, args):
    dw_id = get_playlist_id(sp, "Discover Weekly")
    playlist_tracks = sp.user_playlist_tracks(
        user=args.username, 
        playlist_id=dw_id)["items"]
    tracks = [x["track"] for x in playlist_tracks]
    ids, names, artists  = [], [], []
    for track in tracks:
        ids.append(track["id"])
        names.append(track["name"])
        artists.append(", ".join(x["name"] for x in track["artists"]))
    return ids, names, artists


def create_weekly(sp, args, ids):
    weekly_playlist_name = parse_playlist_name(args.weekly_name_template)
    # check if playlist exists already
    playlist_id = get_playlist_id(sp, weekly_playlist_name)
    if not playlist_id:
        # create playlist
        sp.user_playlist_create(
            user=args.username, 
            name=weekly_playlist_name, 
            public=False, 
            description="Automatically created by Discovered Weekly.")

        # find playlist id
        playlist_id = get_playlist_id(sp, weekly_playlist_name)

        # add tracks to playlist
        sp.user_playlist_add_tracks(
            user=args.username, 
            playlist_id=playlist_id, 
            tracks=ids)

def create_full(sp, args, ids):
    name = args.full_playlist_name

    # Check if playlist already exists
    full_playlist_id = get_playlist_id(sp, name)
    if not full_playlist_id:
        sp.user_playlist_create(user=args.username, name=name, public=False, description="Automatically created by Discovered Weekly.")
        full_playlist_id = get_playlist_id(sp, name)

    # Check for duplicates in recently added tracks
    playlist_tracks = sp.user_playlist_tracks(
        user=args.username, 
        playlist_id=full_playlist_id)["items"]
    existing_ids = [x["track"]["id"] for x in playlist_tracks]
    new_ids = [x for x in ids if x not in existing_ids]
    
    # Add tracks to playlist
    if len(new_ids) > 0:
        sp.user_playlist_add_tracks(user=args.username, playlist_id=full_playlist_id, tracks=new_ids)
    


def run_for_user(
    sp,
    username,
    weekly_template_name="Discovered {week_of_year}-{year}",
    full_playlist_name="Discovered Weekly"
    ):
    Args = namedtuple("Args", "username weekly_template_name full_playlist_name")
    args = Args(username, weekly_template_name, full_playlist_name)

    logging.info(f"Extracting for user: {username}")
    ids, names, artists = dw_tracks(sp, args)
    batch = db.batch()
    for track_id, name, artist in zip(ids, names, artists):
        ref = db.collection(u"tracks").document(track_id)
        batch.set(ref, {
            "track_name": name,
            "artist": artist
        })
    batch.commit()
    create_weekly(sp, args, ids)
    create_full(sp, args, ids)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
    logging.info(f"Started app instance at {datetime.now()}")