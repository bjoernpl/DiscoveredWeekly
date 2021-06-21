import os
import sys
import logging
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
            token = token_ref.get()
            if token.exists:
                token_info = token.to_dict()
                return token_info
        return cached_token
            
    def save_token_to_cache(self, token_info):
        self.cacheHandler.save_token_to_cache(token_info)
        self.db.collection("tokens").document(self.username).set(token_info)
    

handler = logging.StreamHandler(sys.stdout)
logging.basicConfig(handlers=[handler], level=logging.INFO)
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
            access_token = token_info['access_token']
        except SpotifyOauthError as e:
            logging.warning(f"Invalid access token requested: {e}")
            

    if access_token:
        logging.info("Access token successfully added. Getting user info")
        sp = spotipy.Spotify(access_token)
        results = sp.current_user()
        logging.info(f"User results: {results}")
        username = results["id"]
        display_name = results["display_name"]

        cache_handler = FirestoreCacheHandler(username, db)
        cache_handler.save_token_to_cache(token_info)

        # Check if user has followed dw playlist
        dw_id = get_playlist_id(sp, "Discover Weekly")
        if not dw_id:
            # user does not follow dw playlist
            pass

        # cache the dw playlist id for user
        add_user(username, display_name, dw_id)
        return f"You have successfully logged in as {display_name} ({username}). Your 'Discover Weekly' playlist will be copied every monday at 7:00 CET"

    else:
        return "test :D"

@app.route("/error")
def error():
    pass


def get_users():
    users = db.collection(u'users').get()
    return ((user.id, user.to_dict()) for user in users)
    
def add_user(username, display_name, dw_id):
    user = {
        "date_created" : datetime.now(),
        "display_name": display_name,
        "dw_id": dw_id,
        "recent_weekly_id": None,
        "full_playlist_id": None,
        "last_cw": None
    }
    ref = db.collection(u'users').document(username)
    doc = ref.get()
    if not doc.exists:
        ref.set(user)
        logging.info(f"Added user to firestore db: {username}")
    else:
        try:
            doc.get("dw_id")
        except KeyError:
            ref.set(user, merge=["dw_id"])
        logging.info(f"User {username} already exists")


def update_user_playlist_ids(username, recent_id, full_id=None, dw_id=None):
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
            
    ref = db.collection(u'users').document(username)
    ref.set(ids, merge=True)
    logging.info(f"Updated playlist ids for user: {username}")


@app.route("/save_playlists", methods = ['POST'])
def save_playlists():
    code = request.headers.get("passcode", "placeholder")
    if code == os.environ.get("SAVE_PLAYLISTS_CODE"):
        logging.info("Beginning playlist extraction.")
        for user, data in get_users():
            try:
                dw_id = data["dw_id"]
            except KeyError:
                dw_id = get_playlist_id(sp, "Discover Weekly")
                data["dw_id"] = dw_id
            if not dw_id:
                logging.warning(f"No dw id found for: {user}")
                continue

            #if not dw_id:
            #    logging.warning(f"No dw id found for: {user}")
            #    continue
            cache_handler = FirestoreCacheHandler(user, db)
            temp_auth = SpotifyOAuth(
                client_id=os.environ.get("SPOTIFY_CLIENT_ID", "none"), 
                client_secret=os.environ.get("SPOTIFY_CLIENT_SECRET", "none"), 
                redirect_uri="https://pluester.dev/logged_in",
                scope="playlist-modify-private playlist-read-private user-library-read",
                cache_handler=cache_handler)
            token_info = temp_auth.cache_handler.get_cached_token()
            if token_info:
                try:
                    token_info = temp_auth.validate_token(token_info)
                except SpotifyOauthError as e:
                    #TODO  Do correct error handling
                    print("an error occured")
                access_token = token_info['access_token']
                sp = spotipy.Spotify(access_token)
                run_for_user(sp, user, data)
            else:
                logging.warning(f"No token found for user: {user}")
                continue
        return "Success"
    else:
        return "You should not be here. Shoo"

def this_week():
    return datetime.today().isocalendar()[1]

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
        logging.info("\n".join(playlist["name"] for playlist in playlists))
        for playlist in playlists:
            if playlist['name'] == playlist_name:
                playlist_id = playlist['id']
                break
        i += 1
        if not playlists:
            break        
    return playlist_id

def dw_tracks(sp, args):
    dw_id = args.dw_id
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
    results = sp.user_playlist_create(
        user=args.username, 
        name=weekly_playlist_name, 
        public=False, 
        description="Automatically created by Discovered Weekly.")

    # find playlist id
    playlist_id = results["id"]

    # add tracks to playlist
    sp.user_playlist_add_tracks(
        user=args.username, 
        playlist_id=playlist_id, 
        tracks=ids)

    return playlist_id
        

def create_full(sp, args, ids):
    name = args.full_playlist_name
    full_playlist_id = args.full_playlist_id

    if not full_playlist_id:
        results = sp.user_playlist_create(user=args.username, name=name, public=False, description="Automatically created by Discovered Weekly.")
        full_playlist_id = results["id"]

    sp.user_playlist_add_tracks(user=args.username, playlist_id=full_playlist_id, tracks=ids)

    return full_playlist_id



def run_for_user(
    sp,
    username,
    user_data,
    weekly_name_template="Discovered {week_of_year}-{year}",
    full_playlist_name="Discovered Weekly"
    ):
    Args = namedtuple("Args", "username weekly_name_template full_playlist_name dw_id full_playlist_id")
    args = Args(username, weekly_name_template, full_playlist_name, user_data["dw_id"], user_data["full_playlist_id"])

    logging.info(f"Extracting for user: {username}")
    if user_data["last_cw"] != this_week():
        ids, names, artists = dw_tracks(sp, args)
        batch = db.batch()
        for track_id, name, artist in zip(ids, names, artists):
            ref = db.collection(u"tracks").document(track_id)
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
        weekly_id = create_weekly(sp, args, ids)
        full_id = create_full(sp, args, ids)
        update_user_playlist_ids(username, weekly_id, full_id, user_data["dw_id"])
    else:
        logging.warning("Stopped extraction because it has already been run this week")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
    logging.info(f"Started app instance at {datetime.now()}")