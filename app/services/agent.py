from __future__ import annotations

import os
import importlib
from pathlib import Path
from typing import Any

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
            "Always include both 'evidence' and 'source' in your final "
            "response. "
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
        "include one direct quote in evidence, and include "
        "the matching '<game> - <section>' citation in source."
    )


def _extract_agent_output(result: Any) -> AssistantResponse:
    output = getattr(result, "output", None)
    if isinstance(output, AssistantResponse):
        return output

    data = getattr(result, "data", None)
    if isinstance(data, AssistantResponse):
        return data

    raise ValueError("Agent returned an unexpected output shape.")


def _enrich_details(
    game: str,
    prompt: str,
    response: AssistantResponse,
) -> AssistantResponse:
    evidence = response.evidence
    source = response.source

    if evidence and source:
        return response

    chunks = rules_db.retrieve_rules(game=game, query=prompt, top_k=1)
    if chunks:
        best = chunks[0]
        source = source or f"{best.game.title()} - {best.section}"
        evidence = evidence or rules_db.quote_rule(
            best.game,
            best.chunk_id,
            max_chars=420,
            query=prompt,
        )

    evidence = (
        evidence
        or "No direct quote was found for this exact phrasing "
        "in local rule chunks."
    )
    source = source or f"{game.title()} - Source unavailable"

    return AssistantResponse(
        ruling=response.ruling,
        evidence=evidence,
        source=source,
        follow_up=response.follow_up,
    )


def _run_agent_sync(game: str, prompt: str) -> AssistantResponse:
    _ensure_google_credentials()
    user_input = _build_user_input(game, prompt)
    result = _get_rules_agent().run_sync(user_input)
    return _extract_agent_output(result)


async def _run_agent_async(game: str, prompt: str) -> AssistantResponse:
    _ensure_google_credentials()
    user_input = _build_user_input(game, prompt)
    result = await _get_rules_agent().run(user_input)
    return _extract_agent_output(result)


def answer_question(
    prompt: str,
    selected_game: str | None = None,
) -> AssistantResponse:
    game, early_response = _resolve_game(prompt, selected_game)
    if early_response is not None:
        return early_response

    assert game is not None

    try:
        response = _run_agent_sync(game, prompt)
        return _enrich_details(game, prompt, response)
    except Exception:
        return AssistantResponse(
            ruling="I couldn't complete the dynamic rules lookup right now.",
            evidence=(
                "Dynamic lookup failed before citation extraction. "
                "Please try again."
            ),
            source=f"{game.title()} - Source unavailable",
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

    try:
        response = await _run_agent_async(game, prompt)
        return _enrich_details(game, prompt, response)
    except Exception:
        return AssistantResponse(
            ruling="I couldn't complete the dynamic rules lookup right now.",
            evidence=(
                "Dynamic lookup failed before citation extraction. "
                "Please try again."
            ),
            source=f"{game.title()} - Source unavailable",
            follow_up=(
                "Please try again in a moment, or rephrase with "
                "the exact card/role and phase."
            ),
        )
