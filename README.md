# DiscoveredWeekly
Discovered Weekly is a website that automatically copies your <i>Discover Weekly</i> Spotify playlist every week
to ensure that those precious suggestions never get lost. Check out [discoveredweekly.com](https://discoveredweekly.com) for a free hosted version.

This repository contains all code and instructions needed to run the server as a Docker container.

## 1. How it works
The website is built as a Flask app, is written in python, and runs on Gunicorn in a Docker container. The app uses Spotipy to
communicate with the Spotify API. The hosted version is built automatically on commit to the main branch using Google Cloud Build. The built
Docker container is then hosted using Google Cloud Run. As the container can be shut down at any point, and multiple workers can be run,
there is no real internal storage. Instead, Spotify access tokens are saved to a Google Firestore database. Google Cloud Scheduler
runs a POST request weekly on Monday at 7:00 AM CEST to start the process of copying playlists for all users.

## 2. How to run
- Make sure you have Docker installed
- Clone this repo: 
```
git clone git@github.com:bjoernpl/DiscoveredWeekly.git
```
- Set all necessary environment variables in envs.txt (see section 3.)
- Build and name container: 
```
sudo docker build . -t dweekly
```
- Run container with port forwarding and environment variables: 
```
sudo docker run --env-file envs.txt -p 80:8080 -it dweekly
```
This will have started a gunicorn worker process that can be accessed (if run locally) at `0.0.0.0`

## 3. Environment variables
This app needs a few variables set in envs.txt to run properly:
```yaml
# Your Spotify API access data
SPOTIFY_CLIENT_ID=your_spotify_api_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_api_client_secret

# Some password to protect the POST request for
# saving all user's playlists
SAVE_PLAYLISTS_CODE=somepassword

# Flag to enable mock Firestore database for local running
TESTING=True

# URL data for Spotify API authentication requests
BASE_URL=http://0.0.0.0
PORT=8080
```
