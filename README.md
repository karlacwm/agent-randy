
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

- UNO: https://www.bsbwlibrary.org/wp-content/uploads/2023/08/Uno.pdf
- Werewolves: https://www.zygomatic-games.com/wp-content/uploads/2020/04/werewolvesofmillershollow_en_rules_compressed.pdf

## Quickstart

1. Install dependencies:

```bash
uv sync
```

2. Start the API:

```bash
uv run python -m app.main
```

3. Open docs:

`http://localhost:8000/docs`

4. Open the chat UI:

`http://localhost:8000`

## Error handling

- Empty prompt returns a 400 with clear message.
- Unsupported game returns a safe response plus supported game list.
- Unknown scenario returns a clarification request.

## API Endpoints

- `GET /`
- `GET /health`
- `GET /assistant/welcome/{session_id}`
- `POST /assistant/ask`

Example request body:

```json
{
	"session_id": "demo-1",
	"prompt": "In UNO, can I stack a +2 on another +2?"
}
```

## Local Evaluation

Starter eval dataset:
- `data/evaluation_data/eval_data.json`

Current dataset size: 21 cases (normal, edge cases, unsupported game, hallucination traps).

Run local evaluation:

```bash
uv run python -m scripts.run_local_evaluation
```

This script prints pass/fail and pass-rate using simple required-signal checks.

## Project structure

- `app/main.py`: FastAPI app and web UI.
- `app/routers/assistant.py`: API endpoints and request validation.
- `app/services/agent.py`: Deterministic answer assembly.
- `app/services/rules_db.py`: Rule loading, chunking, retrieval, quoting.
- `data/*.md`: Local rule references used for retrieval.


