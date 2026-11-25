"""One game in progress: players, deck, disco ball and the current round."""

import json
from dataclasses import asdict
from pathlib import Path

from hitster_bingo.models import (
    Category,
    Deck,
    DiscoBall,
    GameError,
    Player,
    Side,
    Song,
)


class NoCardError(GameError):
    """Raised when you want to reveal, but no card has been drawn yet."""


class RoundError(GameError):
    """Raised when an action doesn't fit the current moment of the round."""


class Game:
    """Keeps track of everything that happens during one game.

    A round goes: spin -> draw -> reveal -> every player that was right crosses
    a square -> next_turn. Then it's the next player's turn to spin.
    """

    def __init__(
        self,
        deck: Deck,
        side: Side,
        player_names: list[str],
        timer_seconds: int = 30,
        timer_delay: int = 5,
    ):
        if not player_names:
            raise ValueError("A game needs at least one player.")
        self.deck = deck
        self.deck.shuffle()
        self.disco_ball = DiscoBall(side)
        self.players = [Player(name) for name in player_names]
        self.timer_seconds = timer_seconds  # time to write down an answer
        self.timer_delay = timer_delay  # seconds of music before the timer starts
        self.turn = 0  # index of the player whose turn it is
        self.winner: Player | None = None
        self._new_round()

    def _new_round(self) -> None:
        self.current_category: Category | None = None
        self.current_song: Song | None = None
        self.revealed = False
        self.crossed_this_round: set[int] = set()  # player indexes

    @property
    def current_player(self) -> Player:
        return self.players[self.turn]

    # --- The steps of a round ---

    def spin(self) -> Category:
        self._check_not_over()
        if self.current_song is not None:
            raise RoundError("Finish this round first (Volgende beurt).")
        self.current_category = self.disco_ball.spin()
        return self.current_category

    def draw(self) -> Song:
        self._check_not_over()
        if self.current_category is None:
            raise RoundError("Spin the disco ball first.")
        if self.current_song is not None:
            raise RoundError("There's already a card on the table.")
        self.current_song = self.deck.draw()
        return self.current_song

    def reveal(self) -> Song:
        if self.current_song is None:
            raise NoCardError("Draw a card first.")
        self.revealed = True
        return self.current_song

    def cross(self, player_index: int, row: int, col: int) -> None:
        """A player who answered correctly crosses a square of this round's colour."""
        if not self.revealed or self.current_category is None:
            raise RoundError("Reveal the card before crossing squares.")
        if not 0 <= player_index < len(self.players):
            raise RoundError("Unknown player.")
        if player_index in self.crossed_this_round:
            raise RoundError("This player already crossed a square this round.")
        card = self.players[player_index].card
        card.cross(row, col, self.current_category.slot)
        self.crossed_this_round.add(player_index)

    def next_turn(self) -> None:
        """End the round: check for a winner, otherwise pass the turn on."""
        if not self.revealed:
            raise RoundError("Reveal the card before ending the round.")
        self.winner = self._find_winner()
        if self.winner is None:
            self.turn = (self.turn + 1) % len(self.players)
            self._new_round()

    # --- Winning ---

    def bingo_players(self) -> list[Player]:
        return [p for p in self.players if p.card.has_bingo()]

    def _find_winner(self) -> Player | None:
        """Decide the winner, following the tie rule.

        One player with bingo wins. If more players have bingo at the same time,
        the one with the most crosses wins; still equal? Play on.
        """
        candidates = self.bingo_players()
        if not candidates:
            return None
        most = max(len(p.card.crossed) for p in candidates)
        leaders = [p for p in candidates if len(p.card.crossed) == most]
        return leaders[0] if len(leaders) == 1 else None

    def _check_not_over(self) -> None:
        if self.winner is not None:
            raise RoundError(f"The game is over, {self.winner.name} won!")

    # --- Saving and loading ---

    def to_dict(self) -> dict:
        return {
            "side": self.disco_ball.side,
            "deck": self.deck.to_dict(),
            "players": [p.to_dict() for p in self.players],
            "turn": self.turn,
            "timer_seconds": self.timer_seconds,
            "timer_delay": self.timer_delay,
            "winner": self.players.index(self.winner) if self.winner else None,
            "category_slot": self.current_category.slot
            if self.current_category
            else None,
            "song": asdict(self.current_song) if self.current_song else None,
            "revealed": self.revealed,
            "crossed_this_round": sorted(self.crossed_this_round),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Game":
        # Skip __init__ (it would shuffle and make new cards) and fill in directly.
        game = cls.__new__(cls)
        game.deck = Deck.from_dict(data["deck"])
        game.disco_ball = DiscoBall(data["side"])
        game.players = [Player.from_dict(p) for p in data["players"]]
        game.turn = data["turn"]
        game.timer_seconds = data.get("timer_seconds", 30)  # older saves: 30
        game.timer_delay = data.get("timer_delay", 5)  # older saves: 5
        game.winner = (
            game.players[data["winner"]] if data["winner"] is not None else None
        )
        slot = data["category_slot"]
        game.current_category = (
            game.disco_ball.categories[slot] if slot is not None else None
        )
        game.current_song = Song(**data["song"]) if data["song"] else None
        game.revealed = data["revealed"]
        game.crossed_this_round = set(data["crossed_this_round"])
        return game

    def save(self, path: str | Path) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: str | Path) -> "Game":
        with open(path, encoding="utf-8") as f:
            return cls.from_dict(json.load(f))
