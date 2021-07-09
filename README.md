![DiscoveredWeekly](https://socialify.git.ci/bjoernpl/DiscoveredWeekly/image?description=1&descriptionEditable=Discovered%20Weekly%20automatically%20copies%20your%20Discover%20Weekly%20Spotify%20playlist%20so%20you%20never%20lose%20those%20precious%20suggestions.&font=Raleway&language=1&logo=https%3A%2F%2Fclipartart.com%2Fimages%2Fspotify-logo-clipart-2018-1.png&owner=1&pattern=Charlie%20Brown&theme=Dark)
# DiscoveredWeekly
Discovered Weekly is a website that automatically copies your <i>Discover Weekly</i> Spotify playlist every week
to ensure that those precious suggestions never get lost. Check out [discoveredweekly.com](https://discoveredweekly.com) for a free hosted version.

This repository contains all code and instructions needed to run the server as a Docker container.

## 1. How it works
The website is built as a [Flask](https://github.com/pallets/flask/) app and runs on [Gunicorn](https://github.com/benoitc/gunicorn) in a 
[Docker](https://github.com/docker) container. The app uses [Spotipy](https://github.com/plamere/spotipy) to
communicate with the [Spotify API](https://developer.spotify.com/documentation/web-api/). 
The hosted version is built automatically on commit to the main branch using [Google Cloud Build](https://cloud.google.com/build/docs/overview). 
The built Docker container is then hosted using [Google Cloud Run](https://cloud.google.com/run/docs). As the container can be shut down at any point, and multiple workers can be run, there is no real internal storage. 
Instead, Spotify access tokens are saved to a [Google Firestore](https://firebase.google.com/docs/firestore/) database. 
[Google Cloud Scheduler](https://cloud.google.com/scheduler/docs)
runs a POST request weekly on Monday at 7:00 AM CEST to start the process of copying playlists for all users.

## 2. How to run
- Make sure you have Docker installed: https://docs.docker.com/get-docker/
- Clone this repo: 
```
git clone git@github.com:bjoernpl/DiscoveredWeekly.git
```
- Navigate to repo:
```
cd DiscoveredWeekly
```
- Set all necessary environment variables in [envs.txt](https://github.com/bjoernpl/DiscoveredWeekly/blob/main/envs.txt) (see [section 3.](#3-environment-variables))
- Build and name container: 
```
sudo docker build . -t dweekly
```
- Run container with port forwarding and environment variables: 
```
sudo docker run --env-file envs.txt -p 80:8080 -it dweekly
```
This will have started a gunicorn worker process that can be accessed (if run locally) at `0.0.0.0`.

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

## 4. The flow
- The landing screen serves not much more function than to inform the user what the site is about and to present a big button.
- Upon clicking that button, the user is prompted to authenticate via Spotify OAuth.
- (TODO) If the user is not following their Discover Weekly playlist, they are prompted to do so.
- The user then lands on a welcome screen and their Discover Weekly playlist is copied for the first time.
  - A playlist titled `Discovered 29-2021` is created (for calender week 29).
  - A playlist titled `Discovered Weekly` is created where every week's suggestions will be added

## TODOs:
- [x] Add a usable README
- [ ] Code commenting
- [ ] Design the pages
- [ ] Implement prompt to follow Discover Weekly. This is necessary for the service to function.
- [ ] Implement proper opt out possibility. As of now users can only opt out by blocking access to their Spotify account via https://www.spotify.com/us/account/apps/
- [ ] Add some more error handling
- [ ] Add tests
  - Database tests
  - Spotify tests
  - API tests
- [ ] Add Open graph meta tags and share button

