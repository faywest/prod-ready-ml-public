import pytest
from fastapi.testclient import TestClient
from hitster_bingo import api
from hitster_bingo.models import Deck, Song

PLAYERS = {"side": "A", "players": ["Fay", "Sam"]}


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A test client with a small fake songs.json and its own save file."""
    songs_file = tmp_path / "songs.json"
    Deck(
        [
            Song("spotify:track:1", "Secret Title", "Secret Artist", 1987),
            Song("spotify:track:2", "Other Title", "Other Artist", 2004),
        ]
    ).to_json(songs_file)
    monkeypatch.setattr(api, "SONGS_FILE", songs_file)
    monkeypatch.setattr(api, "SAVE_FILE", tmp_path / "savegame.json")
    monkeypatch.setattr(api, "current_game", None)
    return TestClient(api.app)


def test_actions_before_new_game_fail(client):
    assert client.post("/spin").status_code == 409
    assert client.get("/state").status_code == 409


def test_new_game(client):
    state = client.post("/game", json=PLAYERS).json()
    assert [p["name"] for p in state["players"]] == ["Fay", "Sam"]
    assert state["turn"] == 0
    assert state["cards_left"] == 2


def test_timer_setting(client):
    assert client.post("/game", json=PLAYERS).json()["timer_seconds"] == 30
    state = client.post("/game", json={**PLAYERS, "timer_seconds": 45}).json()
    assert state["timer_seconds"] == 45
    too_short = {**PLAYERS, "timer_seconds": 5}
    assert client.post("/game", json=too_short).status_code == 422


def test_timer_delay_setting(client):
    assert client.post("/game", json=PLAYERS).json()["timer_delay"] == 5
    state = client.post("/game", json={**PLAYERS, "timer_delay": 0}).json()
    assert state["timer_delay"] == 0
    too_long = {**PLAYERS, "timer_delay": 30}
    assert client.post("/game", json=too_long).status_code == 422


def test_new_game_validation(client):
    assert (
        client.post("/game", json={"side": "C", "players": ["Fay"]}).status_code == 422
    )
    assert client.post("/game", json={"players": []}).status_code == 422
    assert client.post("/game", json={"players": ["  "]}).status_code == 422


def test_draw_hides_the_answer(client):
    client.post("/game", json=PLAYERS)
    client.post("/spin")
    response = client.post("/draw")
    assert set(response.json()) == {"uri", "cards_left"}
    state = client.get("/state").text
    for text in (response.text, state):
        assert "Title" not in text and "Artist" not in text


def test_wrong_order_gives_409_with_message(client):
    client.post("/game", json=PLAYERS)
    response = client.post("/draw")  # not spun yet
    assert response.status_code == 409
    assert "Spin" in response.json()["detail"]


def test_full_round(client):
    client.post("/game", json=PLAYERS)
    slot = client.post("/spin").json()["slot"]
    client.post("/draw")
    assert client.post("/reveal").json()["title"]
    grid = client.get("/state").json()["players"][0]["grid"]
    row, col = next((r, c) for r in range(5) for c in range(5) if grid[r][c] == slot)
    state = client.post("/cross", json={"player": 0, "row": row, "col": col}).json()
    assert state["players"][0]["crossed"] == [[row, col]]
    state = client.post("/next-turn").json()
    assert state["turn"] == 1
    assert state["category"] is None


def test_game_is_saved(client):
    client.post("/game", json=PLAYERS)
    client.post("/spin")
    saved = api.Game.load(api.SAVE_FILE)
    assert saved.current_category is not None
