import os

from flask import Flask, render_template, request
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from datetime import datetime
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Use the application default credentials
cred = credentials.ApplicationDefault()
firebase_admin.initialize_app(cred, {
  'projectId': "discovered-weekly-316016",
})

db = firestore.client()
auth = SpotifyOAuth(
        client_id=os.environ.get("SPOTIFY_CLIENT_ID", "none"), 
        client_secret=os.environ.get("SPOTIFY_CLIENT_SECRET", "none"), 
        redirect_uri="https://pluester.dev/logged_in",
        scope="playlist-modify-private playlist-read-private user-library-read")
    
app = Flask(__name__)

@app.route("/")
def main():
    auth_url = auth.get_authorize_url()
    return render_template("main.html", auth_url=auth_url)


@app.route("/logged_in")
def logged_in():
    access_token = ""
    token_info = auth.get_cached_token()

    if token_info:
        print("Found cached token!")
        access_token = token_info['access_token']
    else:
        url = request.url
        code = auth.parse_response_code(url)
        if code:
            print("Found Spotify auth code in Request URL! Trying to get valid access token...")
            token_info = auth.get_access_token(code)
            access_token = token_info['access_token']

    if access_token:
        print("Access token available! Trying to get user information...")
        sp = spotipy.Spotify(access_token)
        results = sp.current_user()
        add_user(results["id"])
        return results

    else:
        return "test :D"

def get_users():
    users = db.collection(u'users').get()
    return [user.id for user in users]
    
def add_user(username):
    user = {
        "date_created" : datetime.now()
    }
    ref = db.collection(u'users').document(username)
    if not ref.exists():
        ref.set(user)

@app.route("/save_playlists", methods = ['POST'])
def save_playlists():
    code = request.headers.get("passcode", "placeholder")
    if code == os.environ.get("SAVE_PLAYLISTS_CODE"):
        for user in get_users():
            cache_handler = spotipy.CacheFileHandler(user)
            auth = SpotifyOAuth(
                client_id=os.environ.get("SPOTIFY_CLIENT_ID", "none"), 
                client_secret=os.environ.get("SPOTIFY_CLIENT_SECRET", "none"), 
                redirect_uri="https://pluester.dev/logged_in",
                scope="playlist-modify-private playlist-read-private user-library-read",
                cache_handler=cache_handler)
            token_info = auth.get_cached_token()
            if token_info:
                access_token = token_info['access_token']
                sp = spotipy.Spotify(access_token)
                print(sp.current_user())
            else:
                continue

    else:
        return "You should not be here. Shoo"

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))