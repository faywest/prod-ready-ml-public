"""The FastAPI app: the website talks to these endpoints."""

import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlencode

import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from hitster_bingo.game import Game
from hitster_bingo.import_playlist import import_playlist
from hitster_bingo.models import Category, Deck, GameError, Side
from hitster_bingo.settings import settings

DATA_DIR = Path(__file__).parents[2] / "data"
SONGS_FILE = DATA_DIR / "songs.json"
SAVE_FILE = DATA_DIR / "savegame.json"
STATIC_DIR = Path(__file__).parent / "static"

# One game at a time. It's saved to SAVE_FILE after every change, so a restart
# of the server continues the same game.
current_game: Game | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once when the server starts: load the saved game, if there is one."""
    global current_game
    if SAVE_FILE.exists():
        current_game = Game.load(SAVE_FILE)
    yield


app = FastAPI(title="Hitster Bingo", lifespan=lifespan)

# The DJ's Spotify login, kept in memory only (log in again after a restart).
spotify_auth: dict = {}
SPOTIFY_SCOPES = (
    "streaming user-read-email user-read-private user-modify-playback-state "
    "playlist-read-private"
)


# --- Requests: what the browser sends to us ---


class NewGameRequest(BaseModel):
    side: Side = "A"
    players: list[str] = Field(min_length=1, max_length=10)
    timer_seconds: int = Field(default=30, ge=30, le=60)
    timer_delay: int = Field(default=5, ge=0, le=20)


class CrossRequest(BaseModel):
    player: int
    row: int = Field(ge=0, le=4)
    col: int = Field(ge=0, le=4)


# --- Responses: exactly what each endpoint is allowed to send back ---


class CategoryResponse(BaseModel):
    slot: int
    name: str
    description: str
    symbol: str

    @classmethod
    def from_category(cls, category: Category) -> "CategoryResponse":
        return cls(**category.__dict__)


class HiddenCard(BaseModel):
    """Only what's needed to play the song. No title, artist or year!"""

    uri: str
    cards_left: int


class RevealedCard(BaseModel):
    title: str
    artist: str
    year: int


class PlayerState(BaseModel):
    name: str
    grid: list[list[int]]
    crossed: list[tuple[int, int]]
    crosses_to_bingo: int


class GameState(BaseModel):
    """Everything the page needs to draw the screen. Never contains the answer."""

    side: Side
    players: list[PlayerState]
    turn: int
    timer_seconds: int
    timer_delay: int
    cards_left: int
    category: CategoryResponse | None
    card_drawn: bool
    revealed: bool
    crossed_this_round: list[int]
    bingo: list[str]  # names of players with a full line (could be a tie)
    winner: str | None


# --- Helpers ---


def get_game() -> Game:
    if current_game is None:
        raise HTTPException(status_code=409, detail="Start a new game first.")
    return current_game


def save_game() -> None:
    if current_game is not None:
        current_game.save(SAVE_FILE)


def game_state(game: Game) -> GameState:
    return GameState(
        side=game.disco_ball.side,
        players=[
            PlayerState(
                name=p.name,
                grid=p.card.grid,
                crossed=sorted(p.card.crossed),
                crosses_to_bingo=p.card.crosses_to_bingo(),
            )
            for p in game.players
        ],
        turn=game.turn,
        timer_seconds=game.timer_seconds,
        timer_delay=game.timer_delay,
        cards_left=len(game.deck),
        category=CategoryResponse.from_category(game.current_category)
        if game.current_category
        else None,
        card_drawn=game.current_song is not None,
        revealed=game.revealed,
        crossed_this_round=sorted(game.crossed_this_round),
        bingo=[p.name for p in game.bingo_players()],
        winner=game.winner.name if game.winner else None,
    )


@app.exception_handler(GameError)
def handle_game_error(request: Request, err: GameError) -> JSONResponse:
    """Any 'not allowed' from the game becomes a 409 with the message for the page."""
    return JSONResponse(status_code=409, content={"detail": str(err)})


# --- Endpoints ---


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/game")
def new_game(request: NewGameRequest) -> GameState:
    global current_game
    names = [name.strip() for name in request.players]
    if any(not name for name in names):
        raise HTTPException(status_code=422, detail="Every player needs a name.")
    deck = Deck.from_json(SONGS_FILE)
    if len(deck) == 0:
        raise HTTPException(
            status_code=409,
            detail="songs.json is empty. Log in and open /import first.",
        )
    current_game = Game(
        deck, request.side, names, request.timer_seconds, request.timer_delay
    )
    save_game()
    return game_state(current_game)


@app.get("/state")
def state() -> GameState:
    return game_state(get_game())


@app.post("/spin")
def spin() -> CategoryResponse:
    category = get_game().spin()
    save_game()
    return CategoryResponse.from_category(category)


@app.post("/draw")
def draw() -> HiddenCard:
    game = get_game()
    song = game.draw()
    save_game()
    return HiddenCard(uri=song.uri, cards_left=len(game.deck))


@app.post("/reveal")
def reveal() -> RevealedCard:
    song = get_game().reveal()
    save_game()
    return RevealedCard(title=song.title, artist=song.artist, year=song.year)


@app.post("/cross")
def cross(request: CrossRequest) -> GameState:
    game = get_game()
    game.cross(request.player, request.row, request.col)
    save_game()
    return game_state(game)


@app.post("/next-turn")
def next_turn() -> GameState:
    game = get_game()
    game.next_turn()
    save_game()
    return game_state(game)


@app.get("/import")
def import_songs() -> dict:
    """Save the Spotify playlist as songs.json. Log in with Spotify first."""
    access_token = token()["access_token"]
    try:
        count = import_playlist(settings.playlist_id, access_token, SONGS_FILE)
    except requests.HTTPError as err:
        raise HTTPException(
            status_code=502,
            detail=f"Spotify refused the playlist: {err.response.text}",
        ) from err
    return {
        "saved_songs": count,
        "file": str(SONGS_FILE),
        "tip": "Check the years in songs.json, Spotify sometimes gives remaster years.",
    }


# --- Spotify login for the DJ (OAuth "authorization code" flow) ---


@app.get("/login")
def login() -> RedirectResponse:
    """Step 1: send the DJ to Spotify's login page."""
    state = secrets.token_urlsafe(16)  # random value to check the reply is ours
    spotify_auth["state"] = state
    params = {
        "response_type": "code",
        "client_id": settings.spotify_client_id,
        "scope": SPOTIFY_SCOPES,
        "redirect_uri": settings.spotify_redirect_uri,
        "state": state,
    }
    return RedirectResponse(
        "https://accounts.spotify.com/authorize?" + urlencode(params)
    )


@app.get("/callback")
def callback(code: str, state: str) -> RedirectResponse:
    """Step 2: Spotify sends the DJ back here with a code; swap it for a token."""
    if state != spotify_auth.get("state"):
        raise HTTPException(status_code=400, detail="Login state does not match.")
    _request_token(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.spotify_redirect_uri,
        }
    )
    return RedirectResponse("/")


@app.get("/token")
def token() -> dict:
    """Step 3: the web page asks for the token to start the Spotify player."""
    if "access_token" not in spotify_auth:
        raise HTTPException(status_code=401, detail="Log in with Spotify first.")
    if time.time() > spotify_auth["expires_at"] - 60:  # tokens last 1 hour
        _request_token(
            {
                "grant_type": "refresh_token",
                "refresh_token": spotify_auth["refresh_token"],
            }
        )
    return {"access_token": spotify_auth["access_token"]}


def _request_token(data: dict) -> None:
    response = requests.post(
        "https://accounts.spotify.com/api/token",
        data=data,
        auth=(settings.spotify_client_id, settings.spotify_client_secret),
        timeout=10,
    )
    if not response.ok:
        raise HTTPException(status_code=502, detail=f"Spotify: {response.text}")
    body = response.json()
    spotify_auth["access_token"] = body["access_token"]
    spotify_auth["expires_at"] = time.time() + body["expires_in"]
    if "refresh_token" in body:  # Spotify doesn't always send a new one
        spotify_auth["refresh_token"] = body["refresh_token"]
