from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


DATA_DIR = Path(__file__).resolve().parents[2] / "data"
GAME_FILE_MAP = {
    "uno": DATA_DIR / "uno_rules.md",
    "werewolves": DATA_DIR / "werewolves_rules.md",
}

DEFINED_ENTITIES = {
    "uno": {
        "single": {
            "skip",
            "reverse",
            "wild",
            "+2",
            "+4",
            "0",
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
        },
        "phrases": {
            "draw two",
            "draw 2",
            "wild card",
            "wild draw four",
            "draw four",
            "draw 4",
            "number card",
        },
    },
    "werewolves": {
        "single": {
            "villager",
            "werewolf",
            "werewolves",
            "cupid",
            "seer",
            "witch",
            "hunter",
            "mayor",
        },
        "phrases": {
            "little girl",
            "healing potion",
            "poison potion",
            "role card",
        },
    },
}

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "do",
    "does",
    "for",
    "from",
    "how",
    "i",
    "if",
    "in",
    "is",
    "it",
    "my",
    "of",
    "on",
    "or",
    "the",
    "to",
    "what",
    "when",
    "who",
    "with",
    "you",
    "your",
}

ENTITY_IGNORE_TERMS = {
    "card",
    "cards",
    "role",
    "roles",
    "rule",
    "rules",
    "play",
    "use",
    "does",
    "exist",
    "official",
    "i",
    "can",
    "stack",
    "should",
    "could",
    "would",
    "please",
    "not",
    "my",
    "your",
    "their",
    "turn",
    "when",
    "then",
    "but",
    "color",
    "colour",
    "number",
}


@dataclass
class RuleChunk:
    chunk_id: str
    game: str
    section: str
    text: str


def _normalize_game_name(value: str) -> str:
    key = value.strip().lower().replace(" ", "_")
    aliases = {
        "uno": "uno",
        "werewolves": "werewolves",
        "werewolf": "werewolves",
    }
    return aliases.get(key, key)


def list_games() -> list[str]:
    return sorted(GAME_FILE_MAP.keys())


def normalize_game_choice(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = _normalize_game_name(value)
    if normalized in GAME_FILE_MAP:
        return normalized
    return None


def guess_game_from_prompt(prompt: str) -> str | None:
    text = prompt.lower()
    if "uno" in text:
        return "uno"
    if "werewolves" in text or "werewolf" in text:
        return "werewolves"
    return None


def infer_game_from_entities(prompt: str) -> str | None:
    text = prompt.lower()
    scores: dict[str, int] = {game: 0 for game in GAME_FILE_MAP}

    for game, entities in DEFINED_ENTITIES.items():
        for phrase in entities["phrases"]:
            if phrase in text:
                scores[game] += 2
        for token in entities["single"]:
            if re.search(rf"\b{re.escape(token)}\b", text):
                scores[game] += 1

    best_game = max(scores, key=scores.get)
    if scores[best_game] == 0:
        return None

    # Avoid ambiguous guesses when scores tie.
    top_score = scores[best_game]
    ties = [game for game, score in scores.items() if score == top_score]
    if len(ties) > 1:
        return None

    return best_game


def _split_into_chunks(game: str, full_text: str) -> list[RuleChunk]:
    chunks: list[RuleChunk] = []
    current_section = "General"
    current_lines: list[str] = []
    section_index = 0

    for line in full_text.splitlines():
        if line.startswith("## ") or line.startswith("### "):
            if current_lines:
                chunks.append(
                    RuleChunk(
                        chunk_id=f"{game}:{section_index}",
                        game=game,
                        section=current_section,
                        text="\n".join(current_lines).strip(),
                    )
                )
                section_index += 1
                current_lines = []
            current_section = line.lstrip("# ").strip()
        current_lines.append(line)

    if current_lines:
        chunks.append(
            RuleChunk(
                chunk_id=f"{game}:{section_index}",
                game=game,
                section=current_section,
                text="\n".join(current_lines).strip(),
            )
        )

    return chunks


def load_rule_chunks(game: str) -> list[RuleChunk]:
    normalized_game = _normalize_game_name(game)
    file_path = GAME_FILE_MAP.get(normalized_game)
    if file_path is None:
        raise ValueError(f"Unsupported game: {game}")

    full_text = file_path.read_text(encoding="utf-8")
    return _split_into_chunks(normalized_game, full_text)


def _tokenize(text: str) -> set[str]:
    tokens = re.findall(r"[a-zA-Z0-9+]+", text.lower())
    return {_normalize_token(token) for token in tokens}


def _normalize_token(token: str) -> str:
    value = token.lower().strip()
    for suffix in ("ing", "ed", "es", "s"):
        if len(value) > 5 and value.endswith(suffix):
            return value[: -len(suffix)]
    return value


def _query_terms(query: str) -> list[str]:
    terms = re.findall(r"[a-zA-Z0-9+]+", query.lower())
    return [
        _normalize_token(term)
        for term in terms
        if term not in STOPWORDS and len(term) > 1
    ]


def significant_query_terms(query: str) -> list[str]:
    return [
        term
        for term in _query_terms(query)
        if term not in {"uno", "werewolf", "werewolv", "card", "player", "turn", "game"}
    ]


def retrieve_rules(game: str, query: str, top_k: int = 3) -> list[RuleChunk]:
    if not query.strip():
        return []
    if top_k < 1:
        top_k = 1

    chunks = load_rule_chunks(game)
    query_tokens = _query_terms(query)
    if not query_tokens:
        return chunks[:top_k]

    query_text = query.lower()

    scored: list[tuple[float, RuleChunk]] = []
    for chunk in chunks:
        chunk_text = chunk.text.lower()
        section_text = chunk.section.lower()
        chunk_tokens = _tokenize(chunk_text)

        score = 0.0
        for term in query_tokens:
            if term in chunk_tokens:
                score += 2.0
            else:
                # Prefix fallback helps with forms like "peek" vs "peeking".
                if any(tok.startswith(term[:4]) for tok in chunk_tokens if len(term) >= 4):
                    score += 1.0
            if term in section_text:
                score += 2.5

        # Boost exact phrase overlap for longer keyword sequences.
        for size in (3, 2):
            for idx in range(0, max(0, len(query_tokens) - size + 1)):
                phrase = " ".join(query_tokens[idx : idx + size])
                if phrase and phrase in chunk_text and phrase in query_text:
                    score += 3.5

        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in scored[:top_k]]


def quote_rule(game: str, chunk_id: str, max_chars: int = 800) -> str:
    if max_chars < 40:
        max_chars = 40

    chunks = load_rule_chunks(game)
    for chunk in chunks:
        if chunk.chunk_id == chunk_id:
            quote = chunk.text.replace("\n", " ").strip()
            if len(quote) <= max_chars:
                return quote
            return quote[: max_chars - 3] + "..."
    raise ValueError(f"Chunk not found for game '{game}' and id '{chunk_id}'")


def term_exists_in_game(game: str, term: str) -> bool:
    normalized = _normalize_token(term)
    for chunk in load_rule_chunks(game):
        if normalized in _tokenize(chunk.text):
            return True
    return False


def defined_entities_hint(game: str) -> str:
    entities = DEFINED_ENTITIES.get(game)
    if not entities:
        return ""

    sample = sorted(list(entities["single"]))[:8]
    return ", ".join(sample)


def find_unknown_entities(game: str, prompt: str) -> list[str]:
    entities = DEFINED_ENTITIES.get(game)
    if not entities:
        return []

    text = prompt.lower()
    unknown: set[str] = set()

    # Special case for UNO-style +N cards.
    for plus_card in re.findall(r"\+[0-9]+", text):
        if plus_card not in entities["single"]:
            unknown.add(plus_card)

    # Flag phrase candidates after verbs that usually introduce components.
    pattern = re.compile(r"(?:play|use|choose|draw|is|a|an)\s+([a-z0-9+][a-z0-9+\s-]{0,20})")
    for match in pattern.findall(text):
        candidate = match.strip(" .?!,;:")
        if not candidate or len(candidate) < 2:
            continue

        candidate_tokens = [tok for tok in re.findall(r"[a-z0-9+]+", candidate) if tok]
        if not candidate_tokens:
            continue

        # Keep only compact candidates to avoid overfiring on whole sentences.
        if len(candidate_tokens) > 3:
            continue

        candidate_norm = " ".join(candidate_tokens)
        if candidate_norm in entities["phrases"]:
            continue

        token_check = [tok for tok in candidate_tokens if tok not in ENTITY_IGNORE_TERMS]
        if not token_check:
            continue

        if all(tok in entities["single"] for tok in token_check):
            continue

        # If every meaningful token appears in rules text, do not mark as unknown.
        if all(term_exists_in_game(game, tok) for tok in token_check):
            continue

        unknown.add(candidate_norm)

    return sorted(unknown)
