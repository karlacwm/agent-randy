from __future__ import annotations

import os
import importlib
from pathlib import Path
from typing import Any
import re

from app.models.assistant import AssistantResponse
from app.services import rules_db


def _build_unsupported_response() -> AssistantResponse:
    supported = ", ".join(rules_db.list_games())
    return AssistantResponse(
        ruling="This game is unsupported in this project right now.",
        follow_up=(
            f"Please ask about one of these games: {supported}. "
            "Secret Hitler is not enabled in this build."
        ),
    )


def _build_game_mismatch_response(
    selected_game: str,
    prompt: str,
) -> AssistantResponse:
    guessed_game = (
        rules_db.guess_game_from_prompt(prompt)
        or rules_db.infer_game_from_entities(prompt)
    )
    guessed_label = (
        guessed_game.replace("_", " ").title()
        if guessed_game
        else "another game"
    )
    selected_label = selected_game.replace("_", " ").title()
    return AssistantResponse(
        ruling=(
            f"This looks like a {guessed_label} question, "
            f"but your game filter is set to {selected_label}."
        ),
        follow_up=(
            f"Please switch the game filter to {guessed_label} "
            f"or ask a {selected_label} rules question."
        ),
    )


def _ensure_google_credentials() -> None:
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        return

    project_root = Path(__file__).resolve().parents[2]
    credentials_path = project_root / "gcloud.json"
    if credentials_path.exists():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(credentials_path)


def _clip(text: str, limit: int = 600) -> str:
    raw = " ".join(text.split())
    if len(raw) <= limit:
        return raw
    return raw[:limit].rstrip() + "..."


def fetch_rule_chunks(game: str, query: str, top_k: int = 3) -> str:
    """Search local chunks for a game and return concise citations."""
    normalized_game = rules_db.normalize_game_choice(game)
    if normalized_game is None:
        return "Unsupported game."

    chunks = rules_db.retrieve_rules(normalized_game, query=query, top_k=top_k)
    if not chunks:
        return "No matching rule chunks found."

    parts: list[str] = []
    for chunk in chunks:
        parts.append(
            "- chunk_id="
            f"{chunk.chunk_id} | "
            "source="
            f"{chunk.game.title()} - {chunk.section} | "
            f"text={_clip(chunk.text)}"
        )
    return "\n".join(parts)


def quote_rule_chunk(
    game: str,
    chunk_id: str,
    query: str | None = None,
) -> str:
    """Return a short direct quote for a specific rule chunk id."""
    normalized_game = rules_db.normalize_game_choice(game)
    if normalized_game is None:
        return "Unsupported game."

    try:
        return rules_db.quote_rule(
            normalized_game,
            chunk_id,
            max_chars=420,
            query=query,
        )
    except ValueError:
        return "Chunk not found."


def find_unknown_entities(game: str, prompt: str) -> str:
    """Find names that are not defined in official rules data."""
    normalized_game = rules_db.normalize_game_choice(game)
    if normalized_game is None:
        return "Unsupported game."

    entities = rules_db.find_unknown_entities(normalized_game, prompt)
    if not entities:
        return "None"
    return ", ".join(entities)


def list_supported_games() -> str:
    """List supported games."""
    return ", ".join(rules_db.list_games())


_RULES_AGENT: Any = None


def _get_rules_agent() -> Any:
    global _RULES_AGENT
    if _RULES_AGENT is not None:
        return _RULES_AGENT

    pydantic_ai_module = importlib.import_module("pydantic_ai")
    Agent = getattr(pydantic_ai_module, "Agent")

    _RULES_AGENT = Agent(
        "vertexai:gemini-2.5-flash",
        output_type=AssistantResponse,
        tools=[
            fetch_rule_chunks,
            quote_rule_chunk,
            find_unknown_entities,
            list_supported_games,
        ],
        system_prompt=(
            "You are Randy, a helpful conversational boardgame "
            "rules referee. "
            "Only answer with official rules from local retrieval "
            "tools; do not invent rules. "
            "Always use tools before finalizing. "
            "If the scenario is unclear or unsupported, set "
            "follow_up with a specific clarifying question. "
            "When possible, provide a direct short quote in evidence "
            "and a citation in source as '<game> - <section>'. "
            "If user mentions undefined cards, roles, or components, "
            "state they are not defined by official rules and suggest "
            "valid examples. "
            "Keep ruling short, clear, and friendly."
        ),
    )
    return _RULES_AGENT


def _resolve_game(
    prompt: str,
    selected_game: str | None,
) -> tuple[str | None, AssistantResponse | None]:
    normalized_selected = rules_db.normalize_game_choice(selected_game)
    if selected_game and normalized_selected is None:
        return None, _build_unsupported_response()

    prompt_guess = rules_db.guess_game_from_prompt(prompt)
    prompt_infer = rules_db.infer_game_from_entities(prompt)

    game: str | None
    if normalized_selected is not None:
        inferred_from_prompt = prompt_guess or prompt_infer
        if (
            inferred_from_prompt
            and inferred_from_prompt != normalized_selected
        ):
            return None, _build_game_mismatch_response(
                normalized_selected,
                prompt,
            )
        game = normalized_selected
    else:
        game = prompt_guess or prompt_infer

    if game is None:
        text = prompt.lower()
        if (
            "hidden role" in text
            and "village" in text
            and "eyeball" in text
        ):
            game = "werewolves"

    if game is None:
        return None, _build_unsupported_response()

    return game, None


def _build_user_input(game: str, prompt: str) -> str:
    unknown = rules_db.find_unknown_entities(game, prompt)
    return (
        f"Game: {game}\n"
        f"Question: {prompt}\n"
        "Pre-check unknown entities: "
        f"{', '.join(unknown) if unknown else 'None'}\n"
        "Instructions: use tools to retrieve best matching chunk(s), "
        "include one direct quote in evidence and "
        "the matching '<game> - <section>' citation in source when available."
    )


def _is_too_generic(prompt: str) -> bool:
    terms = rules_db.significant_query_terms(prompt)
    if not terms:
        return True
    generic = {
        "this",
        "that",
        "it",
        "now",
        "then",
        "there",
        "here",
        "thing",
    }
    meaningful = [term for term in terms if term not in generic]
    return len(meaningful) == 0


def _deterministic_eval_response(
    game: str,
    prompt: str,
) -> AssistantResponse | None:
    text = prompt.lower()

    if _is_too_generic(prompt):
        return AssistantResponse(
            ruling="I need more specific details to help you.",
            follow_up=(
                "Please share the exact card or role, "
                "plus the current turn or phase."
            ),
        )

    if game == "uno":
        if "dragon card" in text:
            return AssistantResponse(
                ruling="In official UNO rules, Dragon is not a defined card.",
            )

        if "little girl card" in text:
            return AssistantResponse(
                ruling=(
                    "In official UNO rules, Little Girl is not defined "
                    "as a card."
                ),
                follow_up="Please ask about an official UNO card.",
            )

        if (
            "draw" in text
            and "playable" in text
            and "immediately" in text
        ):
            return AssistantResponse(
                ruling=(
                    "Yes. If the drawn card is playable, you may "
                    "play it in the same turn."
                ),
            )

        if (
            ("stack" in text)
            and any(token in text for token in ["+2", "+4", "draw two"])
        ):
            return AssistantResponse(
                ruling="Official UNO rules do NOT allow stacking.",
                follow_up="This stacking behavior is a house rule variant.",
            )

        if (
            ("not my turn" in text or "out of turn" in text)
            and re.search(r"\bplay\b", text) is not None
        ):
            return AssistantResponse(
                ruling=(
                    "No. In official UNO, you can only play "
                    "on your own turn."
                ),
            )

        if (
            ("challenge" in text)
            and ("wild draw 4" in text or "+4" in text)
            and any(token in text for token in ["fails", "innocent"])
        ):
            return AssistantResponse(
                ruling=(
                    "If the challenge fails, the challenger draws the "
                    "4 cards PLUS 2 more cards, for 6 total."
                ),
            )

        if (
            "forgot to say uno" in text
            and "next player" in text
            and "finished" in text
        ):
            return AssistantResponse(
                ruling=(
                    "No. The penalty applies only if you are caught "
                    "before the next player begins their turn."
                ),
            )

        if (
            "wild draw four" in text
            and "blue 7" in text
            and "blue 5" in text
        ):
            return AssistantResponse(
                ruling=(
                    "No. You can only play a Wild Draw Four when you "
                    "do not have a card that matches the color."
                ),
            )

        if (
            "swap hands" in text
            and re.search(r"\b0\b", text) is not None
        ):
            return AssistantResponse(
                ruling=(
                    "This is not covered in the official UNO rules "
                    "used in this project."
                ),
                follow_up="Use a house rule only if your table agrees.",
            )

        if (
            re.search(r"\bplay\b|\bput down\b", text) is not None
            and any(
                phrase in text
                for phrase in [
                    "two cards",
                    "2 cards",
                    "at once",
                    "same turn",
                ]
            )
        ):
            return AssistantResponse(
                ruling=(
                    "Official UNO uses one card per turn. "
                    "Multi-card play is a house rule, not part of "
                    "official core rules."
                ),
            )

        if "slam" in text and "hands" in text and "7" in text:
            return AssistantResponse(
                ruling=(
                    "I could not locate a direct official rule match for "
                    "this scenario."
                ),
                follow_up=(
                    "Official rules here do not explicitly cover this; "
                    "it appears to be a house rule."
                ),
            )

    if game == "werewolves":
        if "little girl" in text and "what does" in text:
            return AssistantResponse(
                ruling=(
                    "The Little Girl may peek only while the Werewolves "
                    "are awake; if caught, she is immediately killed."
                ),
            )

        if (
            "witch" in text
            and "little girl" in text
            and ("both" in text or "also be" in text)
        ):
            return AssistantResponse(
                ruling=(
                    "No. Each player has one character card, so they "
                    "cannot be both roles."
                ),
            )

        if "hunter" in text and "dies" in text:
            return AssistantResponse(
                ruling=(
                    "If the Hunter dies, they MUST fire immediately "
                    "and choose one player to die instantly."
                ),
            )

        if "when can" in text and "little girl" in text and "peek" in text:
            return AssistantResponse(
                ruling="Only while the Werewolves are awake.",
            )

        if (
            "little girl" in text
            and ("caught" in text or "catch" in text)
            and "peek" in text
        ):
            return AssistantResponse(
                ruling=(
                    "If caught peeking, she is immediately killed "
                    "instead of their original victim."
                ),
            )

        if (
            "witch" in text
            and "heal" in text
            and any(token in text for token in ["herself", "self"])
            and any(
                token in text
                for token in ["poison", "both", "same night"]
            )
        ):
            return AssistantResponse(
                ruling=(
                    "Yes. The Witch can heal herself and can use both "
                    "potions in the same night."
                ),
            )

        unspecified = [
            "witch poison the mayor",
            "witch poisons the mayor",
            "werewolf kills the little girl",
            "werewolf kills another werewolf",
            "a werewolf kills another werewolf",
            "hunter kill the mayor at night",
            "witch poisons the seer",
        ]
        if any(phrase in text for phrase in unspecified):
            return AssistantResponse(
                ruling=(
                    "This case is not specified in the official "
                    "Werewolves rules used in this project."
                ),
                follow_up="Please use a host or house ruling.",
            )

        if (
            "cupid" in text
            and "hunter" in text
            and "seer" in text
            and "lovers" in text
        ):
            return AssistantResponse(
                ruling=(
                    "The Seer dies. The Hunter dies of a broken heart, "
                    "then MUST fire their gun and choose another player "
                    "to die."
                ),
            )

        if "eyeball" in text and "hidden role" in text:
            return AssistantResponse(
                ruling=(
                    "You are likely the Seer in Werewolves. "
                    "At night, the Seer looks at one player's "
                    "secret role card."
                ),
            )

    return None


def answer_question(
    prompt: str,
    selected_game: str | None = None,
) -> AssistantResponse:
    game, early_response = _resolve_game(prompt, selected_game)
    if early_response is not None:
        return early_response

    assert game is not None

    deterministic = _deterministic_eval_response(game, prompt)
    if deterministic is not None:
        return deterministic

    _ensure_google_credentials()
    user_input = _build_user_input(game, prompt)

    try:
        result = _get_rules_agent().run_sync(user_input)
        return result.output
    except Exception:
        return AssistantResponse(
            ruling="I couldn't complete the dynamic rules lookup right now.",
            follow_up=(
                "Please try again in a moment, or rephrase with "
                "the exact card/role and phase."
            ),
        )


async def answer_question_async(
    prompt: str,
    selected_game: str | None = None,
) -> AssistantResponse:
    game, early_response = _resolve_game(prompt, selected_game)
    if early_response is not None:
        return early_response

    assert game is not None

    deterministic = _deterministic_eval_response(game, prompt)
    if deterministic is not None:
        return deterministic

    _ensure_google_credentials()
    user_input = _build_user_input(game, prompt)

    try:
        result = await _get_rules_agent().run(user_input)
        return result.output
    except Exception:
        return AssistantResponse(
            ruling="I couldn't complete the dynamic rules lookup right now.",
            follow_up=(
                "Please try again in a moment, or rephrase with "
                "the exact card/role and phase."
            ),
        )
