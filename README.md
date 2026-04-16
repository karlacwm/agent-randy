
# Agent Randy

The idea and inspiration of this project is:

Everyone needs a Randy to play boardgames with!

This is a project about building an AI agent for a rules-referee agent focused on two games:
- UNO
- Werewolves

The agent answers real game situations with:
- Reference to game rules
- Short reasoning bullets
- Direct citations from local rulebook markdown files
- Explicit undefined-card detection (example: UNO +3 -> not an official defined card)

The current implementation uses a dynamic LLM agent (Randy) with tool-calling:
- Vertex AI Gemini model for conversational reasoning
- Local markdown retrieval tools for grounded rule lookup
- Structured and error-safe API responses

## Rulebook sources

- [UNO](https://www.bsbwlibrary.org/wp-content/uploads/2023/08/Uno.pdf)
- [Werewolves](https://www.zygomatic-games.com/wp-content/uploads/2020/04/werewolvesofmillershollow_en_rules_compressed.pdf)

## What it does

- Answers rule questions from chat prompts.
- Uses local markdown rulebooks.
- Returns `ruling`, `evidence`, `source`, `follow_up`.
- Rejects unsupported games.

## Tech

- FastAPI backend.
- Vertex AI Gemini via tool-calling agent.
- Simple web UI.

## Run

- Install: `uv sync`
- Start: `uv run python -m app.main`
- UI: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`

## API

- `GET /`
- `GET /health`
- `GET /assistant/welcome/{session_id}`
- `POST /assistant/ask`

## Evaluation

- Data: `data/evaluation_data/eval_data.json`
- Run: `uv run python -m scripts.run_local_evaluation`
- Uses semantic scoring for LLM-style answers.

## Files

- `app/main.py` — app + UI
- `app/routers/assistant.py` — endpoints
- `app/services/agent.py` — LLM agent flow
- `app/services/rules_db.py` — rule retrieval
- `data/*.md` — rule sources


