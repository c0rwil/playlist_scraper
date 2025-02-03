from fastapi import FastAPI, HTTPException, Query
from starlette.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import secrets  # for generating state
from dotenv import load_dotenv

from src.scraper import SpotifyDataFetcher

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# Update this to match whatever your Spotify App has set as its "Redirect URI."
# For local dev, it might be http://localhost:5510/callback
REDIRECT_URI = "http://localhost:5510/callback"

app = FastAPI(title="PlaylistScraper")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for your domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# This dictionary simulates storing tokens by 'session_id' or 'state'.
# In a production app, you might store this in Redis or a database.
spotify_sessions = {}


##############################
# Utility / Helper Functions #
##############################

def create_spotify_fetcher(session_id: str) -> SpotifyDataFetcher:
    """
    Instantiates a new SpotifyDataFetcher for each user/session.
    If the session ID already exists, returns the existing fetcher.
    """
    if session_id not in spotify_sessions:
        spotify_sessions[session_id] = SpotifyDataFetcher(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI)
    return spotify_sessions[session_id]

def get_spotify_fetcher(session_id: str) -> SpotifyDataFetcher:
    """
    Retrieves a SpotifyDataFetcher if available (i.e., user is "logged in").
    """
    fetcher = spotify_sessions.get(session_id)
    if not fetcher or not fetcher.access_token:
        raise HTTPException(status_code=401, detail="User is not authenticated or session not found.")
    return fetcher

####################
# Route Definitions#
####################

@app.get("/")
def read_root():
    return {"message": "Welcome to the Spotify Data Fetcher API"}

@app.get("/login")
def login():
    """
    1. Generates a random state string.
    2. Creates a SpotifyDataFetcher for that state.
    3. Redirects the user to Spotify's authorization page.
    """
    state = secrets.token_hex(16)
    create_spotify_fetcher(state)
    scopes = ["user-top-read", "playlist-read-private"]
    auth_url = spotify_sessions[state].get_auth_url(scopes, state)
    return RedirectResponse(url=auth_url)

@app.get("/callback")
def callback(code: str = Query(None), state: str = Query(None)):
    """
    Spotify redirects the user here with ?code=...&state=...
    1. Verifies the state is valid.
    2. Exchanges the code for an access token.
    3. Redirects to Next.js with the session_id in the query string.
    """
    if not code:
        raise HTTPException(status_code=400, detail="Missing code parameter.")
    if not state or state not in spotify_sessions:
        raise HTTPException(status_code=400, detail="State is missing or invalid.")

    fetcher = spotify_sessions[state]
    try:
        fetcher.exchange_code_for_token(code)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error exchanging code for token: {str(e)}")

    # IMPORTANT: Now redirect to Next.js with session_id
    # Adjust the URL below to match your Next.js server address and callback handling route.
    # For local dev, Next typically runs on http://localhost:3000
    redirect_url = f"http://localhost:3000/api/handle_callback?session_id={state}"
    return RedirectResponse(url=redirect_url)

@app.get("/user-profile")
def get_user_profile(session_id: str = Query(...)):
    fetcher = get_spotify_fetcher(session_id)
    try:
        fetcher.fetch_user_profile()
        return fetcher.user_profile
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/top-artists")
def top_artists(session_id: str = Query(...)):
    fetcher = get_spotify_fetcher(session_id)
    try:
        fetcher.fetch_user_top_artists()
        return fetcher.user_top_artists
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/top-tracks")
def top_tracks(session_id: str = Query(...)):
    fetcher = get_spotify_fetcher(session_id)
    try:
        fetcher.fetch_user_top_tracks()
        return fetcher.user_top_tracks
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/playlists")
def playlists(session_id: str = Query(...)):
    fetcher = get_spotify_fetcher(session_id)
    try:
        fetcher.fetch_user_playlists()
        return fetcher.user_playlists
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/playlist-items")
def get_playlist_items(
    playlist_id: str,
    session_id: str = Query(...),
    market: str = Query(None),
    fields: str = Query(None),
    additional_types: str = Query(None),
):
    fetcher = get_spotify_fetcher(session_id)
    try:
        items = fetcher.fetch_playlist_items(
            playlist_id=playlist_id,
            market=market,
            fields=fields,
            additional_types=additional_types
        )
        return items
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

def run():
    uvicorn.run("src.api:app", host="localhost", port=5510, reload=True)
