import requests
import base64
from urllib.parse import urlencode
from concurrent.futures import ThreadPoolExecutor, as_completed

class SpotifyDataFetcher:
    AUTH_URL = "https://accounts.spotify.com/authorize"
    TOKEN_URL = "https://accounts.spotify.com/api/token"

    def __init__(self, client_id, client_secret, redirect_uri):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.access_token = None
        self.refresh_token = None
        self.token_type = None

        self.user_playlists = {}
        self.user_top_artists = []
        self.user_top_tracks = []
        self.user_profile = {}

    def get_auth_url(self, scopes, state):
        """
        Generates the URL for user authorization, including the state parameter.
        """
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(scopes),
            "show_dialog": "true",
            "state": state,  # Use random state to protect against CSRF
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    def exchange_code_for_token(self, code):
        """
        Exchange the authorization code for an access token.
        """
        headers = {
            "Authorization": "Basic "
            + base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode(),
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
        }
        response = requests.post(self.TOKEN_URL, headers=headers, data=data)
        response.raise_for_status()  # Raises an HTTPError if the status is 4xx, 5xx
        token_info = response.json()

        self.access_token = token_info["access_token"]
        self.refresh_token = token_info.get("refresh_token")
        self.token_type = token_info["token_type"]

    def refresh_access_token(self):
        """
        Refresh the access token using the refresh token.
        """
        if not self.refresh_token:
            raise Exception("No refresh token available to refresh the access token.")

        headers = {
            "Authorization": "Basic "
            + base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode(),
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
        }
        response = requests.post(self.TOKEN_URL, headers=headers, data=data)
        response.raise_for_status()
        token_info = response.json()

        self.access_token = token_info["access_token"]
        self.token_type = token_info["token_type"]

    def set_headers(self):
        """
        Helper method to set the authorization headers for Spotify API requests.
        """
        if not self.access_token:
            raise Exception("Access token not set.")
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def fetch_user_top_artists(self, time_range="long_term"):
        base_url = f"https://api.spotify.com/v1/me/top/artists?time_range={time_range}&limit=50"
        response = requests.get(base_url, headers=self.set_headers())
        response.raise_for_status()
        data = response.json()

        self.user_top_artists = [
            {
                "id": artist["id"],
                "name": artist["name"],
                "genres": artist["genres"],
                "popularity": artist["popularity"],
                "followers": artist["followers"]["total"],
            }
            for artist in data["items"]
        ]

    def fetch_user_top_tracks(self, time_range="long_term"):
        base_url = f"https://api.spotify.com/v1/me/top/tracks?time_range={time_range}&limit=50"
        response = requests.get(base_url, headers=self.set_headers())
        response.raise_for_status()
        data = response.json()

        self.user_top_tracks = [
            {
                "id": track["id"],
                "name": track["name"],
                "artists": [artist["name"] for artist in track["artists"]],
                "album": track["album"]["name"],
                "duration_ms": track["duration_ms"],
            }
            for track in data["items"]
        ]

    def fetch_user_profile(self):
        base_url = "https://api.spotify.com/v1/me"
        response = requests.get(base_url, headers=self.set_headers())
        response.raise_for_status()
        data = response.json()

        self.user_profile = {
            "display_name": data["display_name"],
            "profile_picture": data["images"][0]["url"] if data.get("images") else None,
        }

    def fetch_playlist_details(self, playlist):
        response = requests.get(playlist["href"], headers=self.set_headers())
        response.raise_for_status()
        playlist_data = response.json()

        return {
            "id": playlist_data["id"],
            "name": playlist_data["name"],
            "total_tracks": playlist_data["tracks"]["total"],
            "cover_image": playlist_data["images"][0]["url"] if playlist_data.get("images") else None,
        }

    def fetch_user_playlists(self):
        base_url = "https://api.spotify.com/v1/me/playlists"
        response = requests.get(base_url, headers=self.set_headers())
        response.raise_for_status()
        playlists_data = response.json()

        self.user_playlists.clear()
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(self.fetch_playlist_details, playlist) for playlist in playlists_data["items"]]
            for future in as_completed(futures):
                playlist_details = future.result()
                self.user_playlists[playlist_details["name"]] = playlist_details

    def fetch_playlist_items(self, playlist_id, market=None, fields=None, additional_types=None):
        base_url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
        params = {
            "market": market,
            "fields": fields,
            "limit": 50,
            "offset": 0,
            "additional_types": additional_types,
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}

        items = []
        while True:
            response = requests.get(base_url, headers=self.set_headers(), params=params)
            response.raise_for_status()
            response_data = response.json()
            items.extend(response_data.get("items", []))

            if len(items) >= response_data.get("total", 0):
                break

            params["offset"] += 50

        return items
