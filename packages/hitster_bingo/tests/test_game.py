import pytest
from hitster_bingo.game import Game, RoundError
from hitster_bingo.models import Deck, Song


@pytest.fixture
def game():
    songs = [
        Song(f"spotify:track:{i}", f"Title {i}", "Artist", 1980 + i) for i in range(20)
    ]
    return Game(Deck(songs), "A", ["Fay", "Sam", "Noor"])


def free_square(game, player_index):
    """A free square on this player's card in the colour of this round."""
    card = game.players[player_index].card
    return card.free_cells(game.current_category.slot)[0]


def play_round(game, crossing_players=()):
    game.spin()
    game.draw()
    game.reveal()
    for i in crossing_players:
        game.cross(i, *free_square(game, i))
    game.next_turn()


def test_turn_goes_around_the_table(game):
    assert game.current_player.name == "Fay"
    play_round(game)
    assert game.current_player.name == "Sam"
    play_round(game)
    play_round(game)
    assert game.current_player.name == "Fay"


def test_round_order_is_enforced(game):
    with pytest.raises(RoundError):
        game.draw()  # not spun yet
    game.spin()
    game.draw()
    with pytest.raises(RoundError):
        game.cross(0, 0, 0)  # not revealed yet
    with pytest.raises(RoundError):
        game.next_turn()  # not revealed yet


def test_only_one_cross_per_player_per_round(game):
    game.spin()
    game.draw()
    game.reveal()
    game.cross(0, *free_square(game, 0))
    with pytest.raises(RoundError):
        game.cross(0, *free_square(game, 0))


def test_full_line_wins(game):
    card = game.players[1].card
    for c in range(4):
        card.crossed.add((0, c))
    game.spin()
    game.draw()
    game.reveal()
    # give Sam the missing square, whatever colour the disco ball chose
    game.current_category = game.disco_ball.categories[card.grid[0][4]]
    game.cross(1, 0, 4)
    game.next_turn()
    assert game.winner.name == "Sam"
    with pytest.raises(RoundError):
        game.spin()


def test_tie_plays_on_until_someone_has_more(game):
    for p in game.players[:2]:
        p.card.crossed.update((0, c) for c in range(5))
    play_round(game)
    assert game.winner is None  # Fay and Sam both 5 crosses: play on
    play_round(game, crossing_players=[0])
    assert game.winner.name == "Fay"


def test_save_and_load(game, tmp_path):
    game.spin()
    game.draw()
    path = tmp_path / "save.json"
    game.save(path)
    loaded = Game.load(path)
    assert loaded.to_dict() == game.to_dict()
