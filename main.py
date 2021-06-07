import os

from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def main():
    name = os.environ.get("NAME", "World")
    return render_template("main.html")

@app.route("/login")
def login():
    return "You are trying to log in!"


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))