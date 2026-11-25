"""The game pieces: songs, the deck, the disco ball, bingo cards and players."""

import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

Side = Literal["A", "B"]


@dataclass(frozen=True)
class Song:
    """One music card: the front is a Spotify link, the back is the answer."""

    uri: str
    title: str
    artist: str
    year: int


class GameError(Exception):
    """Base class for everything that's "not allowed" in the game."""


class EmptyDeckError(GameError):
    """Raised when you try to draw from a deck without cards."""


class CrossError(GameError):
    """Raised when a square on a bingo card can't be crossed."""


class Deck:
    """A pile of song cards, like the card Deck from the OOP notebooks."""

    def __init__(self, songs: list[Song]):
        self.cards = list(songs)
        self.dealt_cards: list[Song] = []

    @classmethod
    def from_json(cls, path: str | Path) -> "Deck":
        """Build a deck from a JSON file with a list of songs."""
        with open(path, encoding="utf-8") as f:
            rows = json.load(f)
        return cls([Song(**row) for row in rows])

    def to_json(self, path: str | Path) -> None:
        """Save the cards in the deck to a JSON file."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump([asdict(s) for s in self.cards], f, indent=2, ensure_ascii=False)

    def __len__(self) -> int:
        return len(self.cards)

    def __getitem__(self, key):
        return self.cards[key]

    def __repr__(self) -> str:
        return f"Deck({len(self)} cards left, {len(self.dealt_cards)} dealt)"

    def to_dict(self) -> dict:
        """Everything needed to rebuild this deck later (for saving the game)."""
        return {
            "cards": [asdict(s) for s in self.cards],
            "dealt_cards": [asdict(s) for s in self.dealt_cards],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Deck":
        deck = cls([Song(**row) for row in data["cards"]])
        deck.dealt_cards = [Song(**row) for row in data["dealt_cards"]]
        return deck

    def shuffle(self) -> None:
        """Shuffle the cards that are still in the deck."""
        random.shuffle(self.cards)

    def draw(self) -> Song:
        """Take the top card from the deck."""
        if not self.cards:
            raise EmptyDeckError("The deck is empty, start a new game.")
        song = self.cards.pop()
        self.dealt_cards.append(song)
        return song


@dataclass(frozen=True)
class Category:
    """One slot on the disco ball."""

    slot: int  # 0-4, decides the neon colour on the website
    name: str
    description: str
    symbol: str


CATEGORIES: dict[str, list[Category]] = {
    "A": [
        Category(
            0,
            "Groep of soloartiest",
            "Schrijf 'groep' of 'solo'. Een duet telt als groep.",
            "🎤",
        ),
        Category(1, "Vóór 2000?", "Schrijf 'ja' of 'nee'.", "20/00"),
        Category(
            2,
            "4 jaar ervoor of erna",
            "Schrijf een jaartal. Max. 4 jaar ernaast = punt. "
            "Exact goed? Haal een kruisje weg bij een tegenstander.",
            "±4",
        ),
        Category(3, "Decennium", "Schrijf het decennium, bijv. de jaren '80.", "'80s"),
        Category(
            4,
            "2 jaar ervoor of erna",
            "Schrijf een jaartal. Max. 2 jaar ernaast = punt. "
            "Exact goed? Haal een kruisje weg bij een tegenstander.",
            "±2",
        ),
    ],
    "B": [
        Category(
            0,
            "Songtitel",
            "Schrijf de titel. Bijna goed? De andere spelers beslissen samen.",
            "♫",
        ),
        Category(1, "Exacte jaar", "Schrijf het jaar. Alleen exact telt.", "◎"),
        Category(
            2,
            "Naam van groep of zanger(es)",
            "Schrijf de artiest. Bij een samenwerking is de hoofdartiest genoeg.",
            "🎙",
        ),
        Category(3, "Decennium", "Schrijf het decennium, bijv. de jaren '80.", "'80s"),
        Category(
            4,
            "3 jaar ervoor of erna",
            "Schrijf een jaartal. Max. 3 jaar ernaast = punt.",
            "±3",
        ),
    ],
}


class DiscoBall:
    """Spins and lands on one of the five categories of the chosen side."""

    def __init__(self, side: Side = "A"):
        if side not in CATEGORIES:
            raise ValueError(f"Side must be 'A' or 'B', not {side!r}")
        self.side = side
        self.categories = CATEGORIES[side]

    def __repr__(self) -> str:
        return f"DiscoBall(side={self.side!r})"

    def spin(self) -> Category:
        """Spin the disco ball and return the category it lands on."""
        return random.choice(self.categories)


Cell = tuple[int, int]  # (row, col)


@dataclass
class BingoCard:
    """A 5x5 score card. Every square has the colour (slot) of one category.

    Like a sudoku, every row, every column and both diagonals have each colour
    exactly once, so you need all five categories for any bingo line.
    """

    grid: list[list[int]]  # grid[row][col] = slot 0-4
    crossed: set[Cell] = field(default_factory=set)

    SIZE = 5

    @classmethod
    def random(cls) -> "BingoCard":
        """Make a random card: start from a simple pattern and shuffle it."""
        n = cls.SIZE
        while True:
            rows = random.sample(range(n), n)  # random order of rows
            cols = random.sample(range(n), n)  # random order of columns
            colours = random.sample(range(n), n)  # random colour for each number
            # (r + c) % n gives each number once per row and column; shuffling
            # rows, columns and colours keeps that true but makes cards different.
            card = cls([[colours[(r + c) % n] for c in cols] for r in rows])
            # The diagonals are not guaranteed, so try again until they're fair too.
            if all(
                len({card.grid[r][c] for r, c in line}) == n for line in card.lines()
            ):
                return card

    def __repr__(self) -> str:
        return (
            f"BingoCard({len(self.crossed)} crossed, {self.crosses_to_bingo()} to go)"
        )

    def free_cells(self, slot: int) -> list[Cell]:
        """All squares of this colour that are not crossed yet."""
        return [
            (r, c)
            for r in range(self.SIZE)
            for c in range(self.SIZE)
            if self.grid[r][c] == slot and (r, c) not in self.crossed
        ]

    def cross(self, row: int, col: int, slot: int) -> None:
        """Put a cross on a square, if it has the right colour and is still free."""
        if not (0 <= row < self.SIZE and 0 <= col < self.SIZE):
            raise CrossError("That square is not on the card.")
        if self.grid[row][col] != slot:
            raise CrossError("That square has the wrong colour for this category.")
        if (row, col) in self.crossed:
            raise CrossError("That square is already crossed.")
        self.crossed.add((row, col))

    def lines(self) -> list[list[Cell]]:
        """All 12 ways to make bingo: 5 rows, 5 columns and 2 diagonals."""
        n = range(self.SIZE)
        rows = [[(r, c) for c in n] for r in n]
        cols = [[(r, c) for r in n] for c in n]
        diagonals = [[(i, i) for i in n], [(i, self.SIZE - 1 - i) for i in n]]
        return rows + cols + diagonals

    def crosses_to_bingo(self) -> int:
        """How many crosses are still missing in the line that's closest to full."""
        return min(
            sum(cell not in self.crossed for cell in line) for line in self.lines()
        )

    def has_bingo(self) -> bool:
        return self.crosses_to_bingo() == 0

    def to_dict(self) -> dict:
        return {"grid": self.grid, "crossed": sorted(self.crossed)}

    @classmethod
    def from_dict(cls, data: dict) -> "BingoCard":
        return cls(data["grid"], {tuple(cell) for cell in data["crossed"]})


@dataclass
class Player:
    """A player (or team) with their own bingo card."""

    name: str
    card: BingoCard = field(default_factory=BingoCard.random)

    def to_dict(self) -> dict:
        return {"name": self.name, "card": self.card.to_dict()}

    @classmethod
    def from_dict(cls, data: dict) -> "Player":
        return cls(data["name"], BingoCard.from_dict(data["card"]))
