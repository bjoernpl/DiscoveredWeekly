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
app = Flask(__name__)

@app.route("/")
def main():
    name = os.environ.get("NAME", "World")
    return render_template("main.html")

@app.route("/login")
def login():
    sp = authorize_spotify()
    return sp.current_user()

@app.route("/logged_in")
def logged_in():
    return "this is a test"

@app.route("/users")
def get_users():
    users = db.collection(u'users').get()
    users = [user.id for user in users]
    return f"users: {users}"

@app.route("/add_user/<username>")
def add_user(username):
    user = {
        "date_created" : datetime.now()
    }
    db.collection(u'users').document(username).set(user)
    return f"Added user with username : {username}"

@app.route("/save_playlists", methods = ['POST'])
def save_playlists():
    code = request.headers.get("passcode", "placeholder")
    if code == os.environ.get("SAVE_PLAYLISTS_CODE"):
        return "Great success"
    else:
        return "You should not be here. Shoo"

def authorize_spotify():
    token = SpotifyOAuth(
        client_id=os.environ.get("SPOTIFY_CLIENT_ID", "none"), 
        client_secret=os.environ.get("SPOTIFY_CLIENT_SECRET", "none"), 
        redirect_uri="https://pluester.dev/logged_in",
        scope="playlist-modify-private playlist-read-private user-library-read")

    return spotipy.Spotify(auth_manager=token)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))