import pytest
from hitster_bingo.models import (
    CATEGORIES,
    BingoCard,
    CrossError,
    Deck,
    DiscoBall,
    EmptyDeckError,
    Player,
    Song,
)


@pytest.fixture
def songs():
    return [
        Song("spotify:track:1", "Song One", "Artist A", 1985),
        Song("spotify:track:2", "Song Two", "Artist B", 1999),
        Song("spotify:track:3", "Song Three", "Artist C", 2012),
    ]


def test_deck_len(songs):
    assert len(Deck(songs)) == 3


def test_draw_takes_top_card(songs):
    deck = Deck(songs)
    card = deck.draw()
    assert card == songs[-1]
    assert len(deck) == 2
    assert deck.dealt_cards == [card]


def test_draw_from_empty_deck_raises():
    with pytest.raises(EmptyDeckError):
        Deck([]).draw()


def test_shuffle_keeps_all_cards(songs):
    deck = Deck(songs)
    deck.shuffle()
    assert sorted(deck.cards, key=lambda s: s.uri) == songs


def test_json_roundtrip(songs, tmp_path):
    path = tmp_path / "songs.json"
    Deck(songs).to_json(path)
    assert Deck.from_json(path).cards == songs


@pytest.mark.parametrize("side", ["A", "B"])
def test_spin_lands_on_category_of_side(side):
    ball = DiscoBall(side)
    for _ in range(50):
        assert ball.spin() in CATEGORIES[side]


def test_disco_ball_rejects_unknown_side():
    with pytest.raises(ValueError):
        DiscoBall("C")


# --- BingoCard ---


@pytest.fixture
def card():
    return BingoCard.random()


def test_every_line_has_every_colour(card):
    for line in card.lines():
        assert sorted(card.grid[r][c] for r, c in line) == [0, 1, 2, 3, 4]


def test_cross_right_colour(card):
    card.cross(0, 0, card.grid[0][0])
    assert (0, 0) in card.crossed


def test_cross_wrong_colour_raises(card):
    wrong = (card.grid[0][0] + 1) % 5
    with pytest.raises(CrossError):
        card.cross(0, 0, wrong)


def test_cross_twice_raises(card):
    card.cross(0, 0, card.grid[0][0])
    with pytest.raises(CrossError):
        card.cross(0, 0, card.grid[0][0])


def test_bingo_on_full_column(card):
    assert card.crosses_to_bingo() == 5
    for r in range(5):
        card.cross(r, 2, card.grid[r][2])
    assert card.has_bingo()


def test_card_dict_roundtrip(card):
    card.cross(1, 1, card.grid[1][1])
    assert BingoCard.from_dict(card.to_dict()) == card


def test_players_get_different_card_objects():
    assert Player("a").card is not Player("b").card
