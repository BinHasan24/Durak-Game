# Durak-Game

A Python implementation of Durak, a traditional Russian card
game, built for the "Python Development Practice" course.

## About the Game

Durak is a trick-based card game for two players, played with a 36-card
deck (6 through Ace, no jokers). One suit is randomly chosen as trump for
the game. Unlike most card games, there's no winner — only a loser: the
last player left holding cards is the "durak" (fool).

## Rules

- **Players:** 2
- **Deck:** 36 cards — ranks 6, 7, 8, 9, 10, J, Q, K, A in all four suits
- **Setup:** Each player is dealt 6 cards. The remaining deck is placed
  face-down as the draw pile, with its bottom card revealed to show the
  trump suit.
- **Attacking:** The attacking player plays one card. They may add more
  cards afterward, but only ranks that already appear among the cards
  currently on the table (up to 6 cards total).
- **Defending:** The defender must beat each attacking card with either a
  higher card of the same suit, or any trump card (trump beats all
  non-trump suits).
- **Taking cards:** If the defender cannot or chooses not to beat a card,
  they pick up all cards currently on the table, and the turn passes to
  the next player.
- **Successful defense:** If the defender beats every attacking card, the
  cards are discarded, and the defender becomes the new attacker.
- **Refilling hands:** After each round, both players draw back up to 6
  cards from the draw pile (the attacker draws first).
- **End of game:** Once the draw pile is empty, players continue with only
  the cards in hand. The first player to run out of cards wins; the last
  player still holding cards loses.
