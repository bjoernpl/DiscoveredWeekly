import os

from flask import Flask, render_template, request
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from datetime import datetime

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
    users = db.collection(u'users').get()
    return f"users: {users}"

@app.route("/add_user/{username}")
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

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))