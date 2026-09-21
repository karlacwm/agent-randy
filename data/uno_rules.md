# UNO: Official Rules

Source: https://www.bsbwlibrary.org/wp-content/uploads/2023/08/Uno.pdf

## Objective
The first player to play all of the cards in their hand points scores points for the cards left in their opponents' hands. The first player to reach 500 points wins the game.

## Setup
- Each player is dealt 7 cards.
- The remaining cards form the DRAW pile.
- The top card of the DRAW pile is turned over to begin a DISCARD pile.

## Turn Structure
- On a player's turn, they must match a card from their hand to the card on the top of the DISCARD pile, either by number, color, or symbol (Action Cards).
- If a player has no matches, they must draw one card from the DRAW pile.
- If the drawn card can be played, the player is free to play it in the same turn. Otherwise, play moves to the next person.
- A player may choose NOT to play a playable card from their hand. If so, they must draw a card.

## Action Cards
- **Draw Two (+2):** The next player must draw 2 cards and miss their turn. This card may only be played on a matching color or on another Draw Two card.
- **Reverse:** Reverses the direction of play. (If play is currently to the left, play changes to the right).
- **Skip:** The next player in line loses their turn.

## Wild Cards
- **Wild Card:** The player who plays this card calls the color that continues play. A Wild card can be played even if the player has another playable card in their hand.
- **Wild Draw Four (+4):** The player who plays this card calls the next color, AND the next player must draw 4 cards and miss their turn.
  - *Restriction:* A player can ONLY play this card when they do NOT have a card in their hand that matches the COLOR of the discard pile. (They can have matching numbers or Action Cards).

## Defined Cards (Official)
- Number cards: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9
- Action cards: Skip, Reverse, Draw Two (+2)
- Wild cards: Wild, Wild Draw Four (+4)
- This project treats cards outside this list (for example +3) as undefined in official core UNO rules.

## End of Round and Scoring
- A round ends when one player plays all their cards.
- The winner scores points based on cards left in opponents' hands.
- Number cards count as face value.
- Action cards and Wild cards carry higher fixed values (check edition details if your deck differs).
- The first player to reach 500 points wins the game.

## Penalties and Challenges
- If a player forgets to say UNO and is caught in time, they draw 2 cards.
- A Wild Draw Four can be challenged by the next player.
- If played illegally, the player who used +4 takes the penalty.
- If played legally, the challenger takes a larger penalty.

## Rule Disputes and Edge Cases
- **Stacking:** Official UNO rules do NOT allow "stacking." If a player plays a Draw Two (+2) or Wild Draw Four (+4), the next player must draw the cards and lose their turn. They CANNOT play another +2 or +4 to pass the penalty to the next person.
- **Saying UNO:** When a player plays their next-to-last card, they must yell "UNO" to indicate they have only one card left. If they forget, and another player catches them before the next player begins their turn, the player who forgot must draw 2 cards as a penalty.
- **Challenging a Wild Draw Four:** If the victim of a +4 suspects it was played illegally (the player actually has the matching color), they can challenge. The challenged player must show their hand. If guilty, the challenged player draws the 4 cards. If innocent, the challenger draws the 4 cards PLUS 2 extra penalty cards (6 total).

## Notes for This Project
- This project uses official-rules-first behavior.
- If your table uses house rules (for example custom stacking), state it explicitly in the prompt.
