# Disco Bingo

A music bingo party game: spin the disco ball, a hidden song plays through Spotify,
everyone writes down an answer on their paper scorecard, then reveal the card.

## How the parts fit together

| File | What it does |
|---|---|
| `src/hitster_bingo/models.py` | Game pieces: `Song`, `Deck`, `Category`, `DiscoBall` |
| `src/hitster_bingo/game.py` | `Game`: one game in progress (deck + disco ball + current round) |
| `src/hitster_bingo/api.py` | FastAPI endpoints the web page calls, plus the Spotify login |
| `src/hitster_bingo/static/index.html` | The web page (HTML + CSS + JavaScript) |
| `src/hitster_bingo/import_playlist.py` | Spotify playlist -> `data/songs.json` (via `/import`) |
| `src/hitster_bingo/settings.py` | Reads Spotify keys from `.env` |

## Setup (once)

1. Go to https://developer.spotify.com/dashboard and create an app.
   - Redirect URI: `http://127.0.0.1:8000/callback`
   - APIs: tick **Web API** and **Web Playback SDK**
2. Copy `.env.example` to `.env` and fill in the Client ID and Client Secret.
3. Save the playlist as a deck: start the app (see *Play*), log in with Spotify,
   then open http://127.0.0.1:8000/import
4. Open `data/songs.json` and fix years that look wrong (remasters!).

## Play

```bash
uv run uvicorn hitster_bingo.api:app --port 8000
```
Open http://127.0.0.1:8000 (use `127.0.0.1`, not `localhost`), log in with the
DJ's Spotify **Premium** account, choose a side and press *Nieuw spel*.

## Tests

```bash
uv run pytest packages/hitster_bingo/tests
```
