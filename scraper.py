import requests
import base64
from urllib.parse import urlencode
from concurrent.futures import ThreadPoolExecutor, as_completed


class SpotifyDataFetcher:
    AUTH_URL = 'https://accounts.spotify.com/authorize'
    TOKEN_URL = 'https://accounts.spotify.com/api/token'

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

    def get_auth_url(self, scopes):
        """
        Generates the URL for user authorization.
        """
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(scopes),
            'show_dialog': 'true',
        }
        url = f"{self.AUTH_URL}?{urlencode(params)}"
        return url

    def exchange_code_for_token(self, code):
        """
        Exchange the authorization code for an access token.
        """
        headers = {
            'Authorization': 'Basic ' + base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode(),
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_uri,
        }
        response = requests.post(self.TOKEN_URL, headers=headers, data=data)
        token_info = response.json()
        self.access_token = token_info['access_token']
        self.refresh_token = token_info['refresh_token']
        self.token_type = token_info['token_type']

    def refresh_access_token(self):
        """
        Refresh the access token using the refresh token.
        """
        headers = {
            'Authorization': 'Basic ' + base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode(),
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
        }
        response = requests.post(self.TOKEN_URL, headers=headers, data=data)
        token_info = response.json()
        self.access_token = token_info['access_token']
        self.token_type = token_info['token_type']

    def set_headers(self):
        """
        Helper method to set the authorization headers for Spotify API requests.
        """
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

    def fetch_user_top_artists(self, time_range='medium_term'):
        """
        Fetch the user's top artists.
        """
        base_url = f'https://api.spotify.com/v1/me/top/artists?time_range={time_range}'
        response = requests.get(base_url, headers=self.set_headers())
        data = response.json()

        self.user_top_artists = [
            {
                'id': artist['id'],
                'name': artist['name'],
                'genres': artist['genres'],
                'popularity': artist['popularity'],
                'followers': artist['followers']['total'],
            }
            for artist in data['items']
        ]

    def fetch_user_top_tracks(self, time_range='medium_term'):
        """
        Fetch the user's top tracks.
        """
        base_url = f'https://api.spotify.com/v1/me/top/tracks?time_range={time_range}'
        response = requests.get(base_url, headers=self.set_headers())
        data = response.json()

        self.user_top_tracks = [
            {
                'id': track['id'],
                'name': track['name'],
                'artists': [artist['name'] for artist in track['artists']],
                'album': track['album']['name'],
                'duration_ms': track['duration_ms']
            }
            for track in data['items']
        ]

    def fetch_playlist_details(self, playlist):
        """
        Fetch detailed information for a single playlist.
        """
        response = requests.get(playlist['href'], headers=self.set_headers())
        playlist_data = response.json()

        return {
            'id': playlist_data['id'],
            'name': playlist_data['name'],
            'total_tracks': playlist_data['tracks']['total'],
            'cover_image': playlist_data['images'][0]['url'] if playlist_data['images'] else None,
        }

    def fetch_user_playlists(self):
        """
        Fetch all playlists created by the user and their details using threading.
        """
        base_url = 'https://api.spotify.com/v1/me/playlists'
        response = requests.get(base_url, headers=self.set_headers())
        playlists_data = response.json()

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(self.fetch_playlist_details, playlist) for playlist in playlists_data['items']]
            for future in as_completed(futures):
                playlist_details = future.result()
                self.user_playlists[playlist_details['name']] = playlist_details

    def print_user_data(self):
        """
        Example method to print stored user data.
        """
        print("User's Top Artists:", self.user_top_artists)
        print("User's Top Tracks:", self.user_top_tracks)
        print("User's Playlists:", self.user_playlists)
