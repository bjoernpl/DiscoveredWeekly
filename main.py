from data.user import User
import os
import sys
import logging
from flask import Flask, render_template, request, redirect
from datetime import datetime
import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyOauthError
from collections import namedtuple
from data.database import Database
from data.cache_handler import LossyCacheHandler
from data.util import this_week
from spotify import SpotifyUtils
    

handler = logging.StreamHandler(sys.stdout)
logging.basicConfig(handlers=[handler], level=logging.INFO)
# Use the application default credentials for firebase admin

database = Database()
spotify_utils = SpotifyUtils(database, None, LossyCacheHandler())

# Flask app
app = Flask(__name__)

@app.route("/")
def main():
    """ Main page
    """
    auth_url = spotify_utils.auth.get_authorize_url()
    logging.debug(f"Authentication URL for user is: {auth_url}")
    return render_template("main.html", auth_url=auth_url)

@app.route("/logged_in")
def logged_in():
    """ Response to successful login authorization. URL here contains auth token
    """
    url = request.url
    username, display_name, dw_id = spotify_utils.auth_response(url)
    if database.user_exists(username):
        return f"You've already logged in as: {username}. Your Discover Weekly will be copied every monday."
    if not dw_id:
        # user does not follow dw playlist
        pass
    else:
        # cache the dw playlist id for user
        user_id, user_data = database.add_user(username, display_name, dw_id)
        out =  f"You have successfully logged in as {display_name} ({username}). Your 'Discover Weekly' playlist will be copied now and every monday at 7:00 CET."
        run_for_user(spotify_utils, user_id, user_data)
    if not dw_id:
        out = f"For this service to work, you must follow your 'Discover Weekly' playlist on spotify. Go to https://www.spotify.com/us/discoverweekly/ and copy the id out of the url to continue."
    return out

@app.route("/error")
def error():
    pass


@app.route("/save_playlists", methods = ['POST'])
def save_playlists():
    code = request.headers.get("passcode", "placeholder")
    if code == os.environ.get("SAVE_PLAYLISTS_CODE"):
        logging.info("Beginning playlist extraction.")
        for username, user in database.get_users():
            spotify = SpotifyUtils(database, username)
            if spotify.authenticate():
                if not user.dw_id:
                    user.dw_id = spotify.get_playlist_id("Discover Weekly")
                    if not user.dw_id:
                        logging.warning(f"No dw id found for: {username}")
                        continue
                run_for_user(spotify, username, user)
        return "Success"
    else:
        return "You should not be here. Shoo"


def run_for_user(
    su: SpotifyUtils,
    username: str,
    user: User,
    weekly_name_template="Discovered {week_of_year}-{year}",
    full_playlist_name="Discovered Weekly"
    ):
    Args = namedtuple("Args", "username weekly_name_template full_playlist_name dw_id full_playlist_id")
    su.args = Args(username, weekly_name_template, full_playlist_name, user.dw_id, user.full_playlist_id)
    logging.info(f"Extracting for user: {username}")
    if user.last_cw != this_week():
        ids, names, artists = su.dw_tracks()
        database.save_tracks(ids, names, artists)

        weekly_id = su.create_weekly(ids)
        full_id = su.create_full(ids)
        database.update_user_playlist_ids(username, weekly_id, full_id, user.dw_id)
    else:
        logging.warning("Stopped extraction because it has already been run this week")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
    logging.info(f"Started app instance at {datetime.now()}")