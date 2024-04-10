from fastapi import FastAPI, HTTPException, Query, RedirectResponse
from scraper import SpotifyDataFetcher  # Make sure to replace with the correct import path
from dotenv import load_dotenv
import os

load_dotenv()
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = "http://localhost:5510/callback"

app = FastAPI()

# Initialize the SpotifyDataFetcher instance (without a user_id for now)
spotify_fetcher = SpotifyDataFetcher(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI)


@app.get("/")
def read_root():
    return {"message": "Spotify Data Fetcher API"}


@app.get("/login")
def login():
    # Define the required scopes
    scopes = ["user-top-read", "playlist-read-private"]
    # Generate the authorization URL
    auth_url = spotify_fetcher.get_auth_url(scopes)
    # Redirect the user to the authorization URL
    return RedirectResponse(url=auth_url)


@app.get("/callback")
def callback(code: str = Query(None)):
    if not code:
        raise HTTPException(status_code=400, detail="Missing code parameter")

    # Exchange the code for an access token
    spotify_fetcher.exchange_code_for_token(code)
    return {"message": "Authentication successful. You can now use the API endpoints."}


@app.get("/top-artists")
def top_artists():
    if not spotify_fetcher.access_token:
        raise HTTPException(status_code=401, detail="User is not authenticated")

    spotify_fetcher.fetch_user_top_artists()
    return spotify_fetcher.user_top_artists


@app.get("/top-tracks")
def top_tracks():
    if not spotify_fetcher.access_token:
        raise HTTPException(status_code=401, detail="User is not authenticated")

    spotify_fetcher.fetch_user_top_tracks()
    return spotify_fetcher.user_top_tracks


@app.get("/playlists")
def playlists():
    if not spotify_fetcher.access_token:
        raise HTTPException(status_code=401, detail="User is not authenticated")

    spotify_fetcher.fetch_user_playlists()
    return spotify_fetcher.user_playlists


def run():
    uvicorn.run("src.api:app", host="localhost", port=5510, reload=True)
