import os

from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/")
def main():
    name = os.environ.get("NAME", "World")
    return render_template("main.html")

@app.route("/login")
def login():
    id = os.environ.get("SPOTIFY_CLIENT_ID")
    return f"You are trying to log in! client id: {id}"

@app.route("/save_playlists", methods = ['POST'])
def save_playlists():
    code = request.headers.get("passcode", "placeholder")
    if code == os.environ.get("SAVE_PLAYLISTS_CODE"):
        return "Great success"
    else:
        return "You should not be here. Shoo"

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))