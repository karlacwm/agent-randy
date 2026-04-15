from __future__ import annotations
import re

from app.models.assistant import AssistantResponse
from app.services import rules_db


def _clean_text(text: str) -> str:
    cleaned = text.replace("**", "").replace("*", "").replace("#", "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _chunk_sentences(text: str) -> list[str]:
    raw = _clean_text(text)
    parts = re.split(r"(?<=[.!?])\s+", raw)
    return [part.strip(" -") for part in parts if len(part.strip()) > 15]


def _best_sentence_for_prompt(prompt: str, chunk_text: str) -> str:
    prompt_terms = set(rules_db.significant_query_terms(prompt))
    sentences = _chunk_sentences(chunk_text)
    if not sentences:
        return _clean_text(chunk_text)[:180]

    best_sentence = sentences[0]
    best_score = -1
    for sentence in sentences:
        sent_terms = set(re.findall(r"[a-zA-Z0-9+]+", sentence.lower()))
        score = len(prompt_terms.intersection(sent_terms))
        if score > best_score:
            best_score = score
            best_sentence = sentence

    return best_sentence


def _natural_ruling(prompt: str, game: str, chunk_text: str) -> str:
    core = _best_sentence_for_prompt(prompt, chunk_text)
    game_label = game.replace("_", " ").title()
    return f"According to official {game_label} rules, {core[0].lower() + core[1:] if len(core) > 1 else core}"


def _citation_from_chunks(chunks: list[rules_db.RuleChunk], prompt: str) -> tuple[str | None, str | None]:
    if not chunks:
        return None, None

    primary = chunks[0]
    source = f"{primary.game.title()} - {primary.section}"
    evidence = rules_db.quote_rule(
        primary.game, primary.chunk_id, max_chars=420, query=prompt)
    return source, evidence


def _build_unsupported_response() -> AssistantResponse:
    supported = ", ".join(rules_db.list_games())
    return AssistantResponse(
        ruling="This game is unsupported in this project right now.",
        follow_up=(
            "Please ask about one of these games: "
            f"{supported}."
        ),
    )


def _build_not_found_response(prompt: str, game: str) -> AssistantResponse:
    text = prompt.lower()

    # Check if prompt is too generic
    if _is_too_generic_for_ruling(prompt):
        return AssistantResponse(
            ruling="I need more specific details to help you.",
            follow_up="Can you describe what you're trying to do? For example, mention specific cards, roles, or game phases.",
        )

    missing_bits: list[str] = []
    if game == "uno":
        if not any(token in text for token in ("+2", "+4", "draw", "reverse", "skip", "wild", "card")):
            missing_bits.append("exact card name")
        if not any(token in text for token in ("turn", "next", "immediately", "before", "after")):
            missing_bits.append("whose turn it is")
    elif game == "werewolves":
        if not any(token in text for token in ("witch", "hunter", "mayor", "little girl", "werewolf", "villager", "role")):
            missing_bits.append("exact role name")
        if not any(token in text for token in ("night", "day", "awake", "discussion", "vote", "phase")):
            missing_bits.append("current phase")

    if not missing_bits:
        follow_up = "Please clarify the exact card or role involved and the current phase/turn order."
    elif len(missing_bits) == 1:
        follow_up = f"Please clarify: {missing_bits[0]}."
    else:
        follow_up = f"Please clarify: {missing_bits[0]} and {missing_bits[1]}."

    return AssistantResponse(
        ruling=(
            "I do not have enough exact context to match this to an official rule with confidence."
        ),
        follow_up=follow_up,
    )


def _build_game_mismatch_response(selected_game: str, prompt: str) -> AssistantResponse:
    guessed_game = rules_db.guess_game_from_prompt(
        prompt) or rules_db.infer_game_from_entities(prompt)
    guessed_label = guessed_game.replace(
        "_", " ").title() if guessed_game else "another game"
    selected_label = selected_game.replace("_", " ").title()
    return AssistantResponse(
        ruling=(
            f"This looks like a {guessed_label} question, but your game filter is set to {selected_label}."
        ),
        follow_up=(
            f"Please switch the game filter to {guessed_label} or ask a {selected_label} rules question."
        ),
    )


def _build_not_specified_response(game: str) -> AssistantResponse:
    game_label = game.replace("_", " ").title()
    return AssistantResponse(
        ruling=(
            f"This case is not specified in the official {game_label} rules used in this project."
        ),
        follow_up=(
            "Please use a host/house ruling for this scenario, or provide exact phase and setup details."
        ),
    )


def _is_too_generic_for_ruling(prompt: str) -> bool:
    generic_terms = {"this", "that", "it",
                     "now", "then", "there", "here", "thing"}
    terms = rules_db.significant_query_terms(prompt)
    if not terms:
        return True
    meaningful = [term for term in terms if term not in generic_terms]
    return len(meaningful) == 0


def _is_werewolves_unspecified_interaction(prompt: str) -> bool:
    text = prompt.lower()

    if "another werewolf" in text or "other werewolf" in text:
        return True

    role_terms = [
        "werewolf",
        "werewolves",
        "witch",
        "mayor",
        "little girl",
        "hunter",
        "seer",
        "cupid",
        "villager",
    ]
    interaction_terms = [
        "kill",
        "kills",
        "killed",
        "poison",
        "poisons",
        "target",
        "targets",
        "attack",
        "attacks",
    ]
    question_terms = [
        "what happens if",
        "can",
        "is it allowed",
    ]

    role_hits = sum(1 for role in role_terms if role in text)
    has_interaction = any(term in text for term in interaction_terms)
    has_question = any(term in text for term in question_terms)

    return role_hits >= 2 and has_interaction and has_question


def _build_unknown_entity_response(game: str, unknown_entities: list[str]) -> AssistantResponse:
    names = ", ".join(unknown_entities)
    hint = rules_db.defined_entities_hint(game)
    game_label = game.replace("_", " ").title()
    if len(unknown_entities) == 1:
        ruling = (
            f"In official {game_label} rules used by this project, {names} is not a defined card or component."
        )
    else:
        ruling = (
            f"In official {game_label} rules used by this project, {names} are not defined cards or components."
        )
    return AssistantResponse(
        ruling=ruling,
        follow_up=(
            "Try a defined card or role instead"
            + (f" (examples: {hint})." if hint else ".")
        ),
    )


def _handle_uno_out_of_turn(prompt: str) -> AssistantResponse | None:
    text = prompt.lower()
    mentions_out_of_turn = (
        "not my turn" in text
        or "not your turn" in text
        or "out of turn" in text
        or "not their turn" in text
    )
    mentions_play_action = (
        "play" in text or "put" in text or "drop" in text
    )

    if not (mentions_out_of_turn and mentions_play_action):
        return None

    chunks = rules_db.retrieve_rules(
        "uno", "on player's turn must match discard", top_k=1)
    if not chunks:
        return AssistantResponse(
            ruling="No. In official UNO, you can only play on your own turn.",
        )

    primary = chunks[0]
    return AssistantResponse(
        ruling=(
            "No. In official UNO, you can only play on your own turn, "
            "even if your card color and number match the discard pile."
        ),
        evidence=rules_db.quote_rule(
            primary.game, primary.chunk_id, max_chars=420, query=prompt),
        source=f"{primary.game.title()} - {primary.section}",
    )


def _handle_uno_wild_draw_four(prompt: str) -> AssistantResponse | None:
    text = prompt.lower()
    if "wild draw four" not in text and "+4" not in text:
        return None

    chunks = rules_db.retrieve_rules(
        "uno", "wild draw four only if no matching color", top_k=1)
    source, evidence = _citation_from_chunks(chunks, prompt)

    return AssistantResponse(
        ruling=(
            "In official UNO, you can play Wild Draw Four only when you do not have a card matching the color "
            "of the discard pile."
        ),
        evidence=evidence,
        source=source,
    )


def _handle_uno_reverse(prompt: str) -> AssistantResponse | None:
    text = prompt.lower()
    if "reverse" not in text:
        return None
    if "what does" not in text and "effect" not in text and "do" not in text:
        return None

    chunks = rules_db.retrieve_rules(
        "uno", "reverse reverses direction of play", top_k=1)
    source, evidence = _citation_from_chunks(chunks, prompt)

    return AssistantResponse(
        ruling="Reverse reverses the direction of play.",
        evidence=evidence,
        source=source,
    )


def _handle_uno_stacking(prompt: str) -> AssistantResponse | None:
    text = prompt.lower()
    if "stack" not in text:
        return None
    if "+2" not in text and "+4" not in text and "draw two" not in text and "draw four" not in text:
        return None

    chunks = rules_db.retrieve_rules("uno", "stacking do not allow", top_k=1)
    source, evidence = _citation_from_chunks(chunks, prompt)

    return AssistantResponse(
        ruling="Official UNO rules do NOT allow stacking draw penalties.",
        evidence=evidence,
        source=source,
    )


def _handle_uno_choose_draw(prompt: str) -> AssistantResponse | None:
    text = prompt.lower()
    if "choose" not in text or "draw" not in text:
        return None
    if "playable" not in text and "can play" not in text:
        return None

    chunks = rules_db.retrieve_rules(
        "uno", "choose not to play a playable card draw a card", top_k=1)
    source, evidence = _citation_from_chunks(chunks, prompt)

    return AssistantResponse(
        ruling="Yes. You may choose NOT to play a playable card and instead draw a card.",
        evidence=evidence,
        source=source,
    )


def _handle_uno_draw_playable(prompt: str) -> AssistantResponse | None:
    text = prompt.lower()
    if "draw" not in text or "play" not in text:
        return None
    if "playable card" not in text:
        return None
    if "same turn" not in text and "immediately" not in text and "may i play" not in text:
        return None

    chunks = rules_db.retrieve_rules(
        "uno", "drawn card can be played in the same turn", top_k=1)
    source, evidence = _citation_from_chunks(chunks, prompt)

    return AssistantResponse(
        ruling="Yes. If the drawn card is playable, you may play it in the same turn.",
        evidence=evidence,
        source=source,
    )


def _handle_uno_unknown_named_card(prompt: str) -> AssistantResponse | None:
    text = prompt.lower()
    match = re.search(r"what does\s+([a-z0-9+\s-]+?)\s+card\s+do", text)
    if not match:
        return None

    card_name = " ".join(match.group(1).split())
    known_named_cards = {
        "skip",
        "reverse",
        "wild",
        "wild draw four",
        "draw two",
        "draw four",
    }
    if card_name in known_named_cards or re.fullmatch(r"\+[24]", card_name):
        return None

    return _build_unknown_entity_response("uno", [card_name])


def _handle_uno_plus4_challenge(prompt: str) -> AssistantResponse | None:
    text = prompt.lower()
    if "+4" not in text and "wild draw four" not in text:
        return None
    if "challenge" not in text or "fails" not in text:
        return None

    chunks = rules_db.retrieve_rules(
        "uno", "challenger draws plus 2 6 total", top_k=1)
    source, evidence = _citation_from_chunks(chunks, prompt)

    return AssistantResponse(
        ruling="If the challenge fails, the challenger draws the 4 cards PLUS 2 more cards, for 6 total.",
        evidence=evidence,
        source=source,
    )


def _handle_uno_multi_card_play(prompt: str) -> AssistantResponse | None:
    text = prompt.lower()

    asks_multi_play = (
        "play two cards" in text
        or "2 cards" in text
        or "two cards" in text
        or "double" in text
        or "at once" in text
        or "same turn" in text
    )
    mentions_matching = (
        "same number" in text
        or "same color" in text
        or "same colour" in text
        or "matching" in text
    )
    mentions_play_action = "play" in text or "put" in text or "drop" in text

    if not (mentions_play_action and asks_multi_play):
        return None

    if not mentions_matching and "one turn" not in text and "same turn" not in text:
        return None

    chunks = rules_db.retrieve_rules(
        "uno", "on player's turn must match discard", top_k=1)
    source, evidence = _citation_from_chunks(chunks, prompt)

    return AssistantResponse(
        ruling=(
            "No. In official UNO rules, you play one card per turn. "
            "Playing two matching cards together is a house rule, not part of official core rules."
        ),
        evidence=evidence,
        source=source,
    )


def _handle_werewolves_role_overlap(prompt: str) -> AssistantResponse | None:
    text = prompt.lower()
    asks_overlap = (
        "also be" in text
        or "at the same time" in text
        or "both" in text
    )
    mentions_witch = "witch" in text
    mentions_little_girl = "little girl" in text

    if not (asks_overlap and mentions_witch and mentions_little_girl):
        return None

    chunks = rules_db.retrieve_rules(
        "werewolves", "each player is secretly dealt one character card", top_k=1)
    source, evidence = _citation_from_chunks(chunks, prompt)

    return AssistantResponse(
        ruling=(
            "No. In standard Werewolves rules used in this project, each player has one character card, "
            "so a player cannot be both the Witch and the Little Girl at the same time."
        ),
        evidence=evidence,
        source=source,
    )


def _handle_werewolves_little_girl(prompt: str) -> AssistantResponse | None:
    text = prompt.lower()
    mentions_little_girl = "little girl" in text
    asks_effect = (
        "what does" in text
        or "what do" in text
        or "how" in text
        or "ability" in text
        or "effect" in text
    )
    if not (mentions_little_girl and asks_effect):
        return None

    chunks = rules_db.retrieve_rules(
        "werewolves", "little girl only while werewolves are awake", top_k=1)
    if not chunks:
        return None

    primary = chunks[0]
    return AssistantResponse(
        ruling=(
            "The Little Girl can secretly peek only while the Werewolves are awake. "
            "If she is caught peeking, she is immediately killed."
        ),
        evidence=rules_db.quote_rule(
            primary.game, primary.chunk_id, max_chars=420, query=prompt),
        source=f"{primary.game.title()} - {primary.section}",
    )


def _handle_werewolves_witch_potions(prompt: str) -> AssistantResponse | None:
    text = prompt.lower()
    mentions_witch = "witch" in text
    mentions_potions = "potion" in text or "potions" in text
    asks_both = "both" in text or "same night" in text or "one night" in text
    if not (mentions_witch and mentions_potions and asks_both):
        return None

    chunks = rules_db.retrieve_rules(
        "werewolves", "witch can use both potions in the same night", top_k=1)
    source, evidence = _citation_from_chunks(chunks, prompt)

    return AssistantResponse(
        ruling="Yes. The Witch can use both potions in the same night.",
        evidence=evidence,
        source=source,
    )


def _handle_werewolves_hunter(prompt: str) -> AssistantResponse | None:
    text = prompt.lower()
    if "hunter" not in text or "dies" not in text:
        return None

    chunks = rules_db.retrieve_rules(
        "werewolves", "hunter must fire and die instantly", top_k=1)
    source, evidence = _citation_from_chunks(chunks, prompt)

    return AssistantResponse(
        ruling=(
            "If the Hunter dies, they MUST fire immediately and choose one other player to die instantly with them."
        ),
        evidence=evidence,
        source=source,
    )


def _handle_werewolves_mayor_death(prompt: str) -> AssistantResponse | None:
    text = prompt.lower()
    if "mayor" not in text or "dies" not in text:
        return None

    chunks = rules_db.retrieve_rules(
        "werewolves", "if mayor is killed choose successor", top_k=1)
    source, evidence = _citation_from_chunks(chunks, prompt)

    return AssistantResponse(
        ruling="If the Mayor dies, they choose their successor.",
        evidence=evidence,
        source=source,
    )


def _handle_werewolves_little_girl_caught(prompt: str) -> AssistantResponse | None:
    text = prompt.lower()
    if "little girl" not in text or "peek" not in text:
        return None
    if "catch" not in text and "caught" not in text:
        return None

    chunks = rules_db.retrieve_rules(
        "werewolves", "little girl immediately killed instead of original victim", top_k=1)
    source, evidence = _citation_from_chunks(chunks, prompt)

    return AssistantResponse(
        ruling="If caught peeking, the Little Girl is immediately killed instead of their original victim.",
        evidence=evidence,
        source=source,
    )


def _handle_werewolves_witch_heal_self(prompt: str) -> AssistantResponse | None:
    text = prompt.lower()
    if "witch" not in text:
        return None
    if "heal herself" not in text and "heal self" not in text and "healing potion on herself" not in text:
        return None

    chunks = rules_db.retrieve_rules(
        "werewolves", "witch can use the healing potion on herself", top_k=1)
    source, evidence = _citation_from_chunks(chunks, prompt)

    return AssistantResponse(
        ruling="Yes. The Witch CAN use the healing potion on herself.",
        evidence=evidence,
        source=source,
    )


def _handle_werewolves_mayor_votes(prompt: str) -> AssistantResponse | None:
    text = prompt.lower()
    if "mayor" not in text:
        return None
    if "how many votes" not in text and "vote" not in text and "two votes" not in text:
        return None

    chunks = rules_db.retrieve_rules(
        "werewolves", "mayor counts as two votes", top_k=1)
    source, evidence = _citation_from_chunks(chunks, prompt)

    return AssistantResponse(
        ruling="The Mayor's vote counts as TWO votes.",
        evidence=evidence,
        source=source,
    )


def answer_question(prompt: str, selected_game: str | None = None) -> AssistantResponse:
    normalized_selected = rules_db.normalize_game_choice(selected_game)
    if selected_game and normalized_selected is None:
        return _build_unsupported_response()

    prompt_guess = rules_db.guess_game_from_prompt(prompt)
    prompt_infer = rules_db.infer_game_from_entities(prompt)

    if normalized_selected is not None:
        inferred_from_prompt = prompt_guess or prompt_infer
        if inferred_from_prompt and inferred_from_prompt != normalized_selected:
            return _build_game_mismatch_response(normalized_selected, prompt)
        game = normalized_selected
    else:
        game = prompt_guess or prompt_infer

    if game is None:
        return _build_unsupported_response()

    if game == "uno":
        # Handle precise known intent patterns before unknown-entity checks.
        multi_card_play = _handle_uno_multi_card_play(prompt)
        if multi_card_play is not None:
            return multi_card_play

        draw_playable = _handle_uno_draw_playable(prompt)
        if draw_playable is not None:
            return draw_playable

        unknown_named_card = _handle_uno_unknown_named_card(prompt)
        if unknown_named_card is not None:
            return unknown_named_card

    if game == "werewolves" and _is_werewolves_unspecified_interaction(prompt):
        return _build_not_specified_response(game)

    unknown_entities = rules_db.find_unknown_entities(game, prompt)
    if unknown_entities:
        return _build_unknown_entity_response(game, unknown_entities)

    if game == "uno":
        multi_card_play = _handle_uno_multi_card_play(prompt)
        if multi_card_play is not None:
            return multi_card_play

        stacking = _handle_uno_stacking(prompt)
        if stacking is not None:
            return stacking

        choose_draw = _handle_uno_choose_draw(prompt)
        if choose_draw is not None:
            return choose_draw

        plus4_challenge = _handle_uno_plus4_challenge(prompt)
        if plus4_challenge is not None:
            return plus4_challenge

        wild_draw_four = _handle_uno_wild_draw_four(prompt)
        if wild_draw_four is not None:
            return wild_draw_four

        reverse = _handle_uno_reverse(prompt)
        if reverse is not None:
            return reverse

        out_of_turn = _handle_uno_out_of_turn(prompt)
        if out_of_turn is not None:
            return out_of_turn

    if game == "werewolves":
        overlap = _handle_werewolves_role_overlap(prompt)
        if overlap is not None:
            return overlap

        little_girl = _handle_werewolves_little_girl(prompt)
        if little_girl is not None:
            return little_girl

        little_girl_caught = _handle_werewolves_little_girl_caught(prompt)
        if little_girl_caught is not None:
            return little_girl_caught

        witch_potions = _handle_werewolves_witch_potions(prompt)
        if witch_potions is not None:
            return witch_potions

        witch_heal_self = _handle_werewolves_witch_heal_self(prompt)
        if witch_heal_self is not None:
            return witch_heal_self

        hunter = _handle_werewolves_hunter(prompt)
        if hunter is not None:
            return hunter

        mayor_votes = _handle_werewolves_mayor_votes(prompt)
        if mayor_votes is not None:
            return mayor_votes

        mayor_death = _handle_werewolves_mayor_death(prompt)
        if mayor_death is not None:
            return mayor_death

    if _is_too_generic_for_ruling(prompt):
        return _build_not_found_response(prompt, game)

    chunks = rules_db.retrieve_rules(game=game, query=prompt, top_k=1)
    if not chunks:
        return _build_not_found_response(prompt, game)

    primary = chunks[0]
    ruling = _natural_ruling(prompt, game, primary.text)

    return AssistantResponse(
        ruling=ruling,
        evidence=rules_db.quote_rule(
            primary.game, primary.chunk_id, max_chars=420, query=prompt),
        source=f"{primary.game.title()} - {primary.section}",
    )
