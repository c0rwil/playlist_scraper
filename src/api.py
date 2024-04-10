from fastapi import FastAPI, HTTPException, Query
from starlette.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from src.scraper import SpotifyDataFetcher
from dotenv import load_dotenv
import os

load_dotenv()
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = "http://localhost:5510/callback"

app = FastAPI(title="PlaylistScraper")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the SpotifyDataFetcher instance (without a user_id for now)
spotify_fetcher = SpotifyDataFetcher(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI)


@app.get("/")
def read_root():
    return {"message": "Spotify Data Fetcher API"}


@app.get("/user-profile")
def get_user_profile():
    if not spotify_fetcher.access_token:
        raise HTTPException(status_code=401, detail="User is not authenticated")
    try:
        spotify_fetcher.fetch_user_profile()
        return spotify_fetcher.user_profile
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

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


# Dependency to ensure the user is authenticated
def get_current_authenticated_user():
    if not spotify_fetcher.access_token:
        raise HTTPException(status_code=401, detail="User is not authenticated")
    return spotify_fetcher


# Endpoint to fetch details for a specific playlist
# @app.get("/playlists/{playlist_id}")
# def playlist_details(playlist_id: str)):
#     playlist = user.user_playlists.get(playlist_id)
#     if not playlist:
#         # If we do not have the playlist cached, fetch it again
#         user.fetch_user_playlists()
#         playlist = user.user_playlists.get(playlist_id)
#         if not playlist:
#             raise HTTPException(status_code=404, detail="Playlist not found")
#     return user.fetch_playlist_details(playlist)


def run():
    uvicorn.run("src.api:app", host="localhost", port=5510, reload=True)
