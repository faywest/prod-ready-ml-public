"""Read the Spotify playlist and save it as data/songs.json.

Only the song *information* (link, title, artist, year) is saved, not the music.

Spotify only shares the songs of a playlist with a logged-in user, so this runs
through the website: log in with Spotify, then open http://127.0.0.1:8000/import
"""

from pathlib import Path

import requests

from hitster_bingo.models import Deck, Song

API = "https://api.spotify.com/v1"
SONGS_FILE = Path(__file__).parents[2] / "data" / "songs.json"


def fetch_songs(playlist_id: str, token: str) -> list[Song]:
    """Read all tracks of a playlist. Spotify gives max 100 per page."""
    url: str | None = f"{API}/playlists/{playlist_id}/items?limit=100"
    headers = {"Authorization": f"Bearer {token}"}
    songs = []
    while url:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        page = response.json()
        for row in page["items"]:
            # Spotify calls the song "track" (old) or "item" (new); accept both
            track = row.get("track") or row.get("item")
            if not track or not track.get("uri"):  # skip removed/local tracks
                continue
            songs.append(
                Song(
                    uri=track["uri"],
                    title=track["name"],
                    artist=", ".join(a["name"] for a in track["artists"]),
                    # release_date looks like "1985-06-01" or "1985"
                    year=int(track["album"]["release_date"][:4]),
                )
            )
        url = page["next"]  # link to the next page, or None at the end
    return songs


def import_playlist(playlist_id: str, token: str, path: Path = SONGS_FILE) -> int:
    """Fetch the playlist and save it as a deck. Returns the number of songs."""
    deck = Deck(fetch_songs(playlist_id, token))
    deck.to_json(path)
    return len(deck)
