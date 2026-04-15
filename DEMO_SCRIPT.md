# 5-Minute Demo Script

## Goal
Show that your agent can resolve real rule disputes with citations, handle edge cases, and fail safely.

## 0) Setup (30 seconds)

Start API:

```bash
uv run python -m app.main
```

Open docs: http://localhost:8000/docs

Initialize session:
- Call `GET /assistant/welcome/demo-live`

## 1) Basic ruling (60 seconds)

Ask:
- `In UNO, can I stack a +2 on another +2?`

What to point out:
- Clear ruling
- Why bullets
- Citation quote

## 2) Edge case (60 seconds)

Ask:
- `In Werewolves, can the Witch also be the Little Girl?`

What to point out:
- Role-combination rule handled correctly
- Response is tied to official text

## 3) Hallucination trap (60 seconds)

Ask:
- `In UNO, what does the Dragon card do?`

What to point out:
- Agent does not invent a fake card rule
- Fallback asks for clarification

## 4) Unsupported game handling (45 seconds)

Ask:
- `In Catan, what does the robber do?`

What to point out:
- Agent states unsupported scope
- Lists supported games cleanly

## 5) Evaluation story (75 seconds)

Run:

```bash
uv run python -m scripts.run_local_evaluation
```

Say:
- Dataset covers normal rules, edge cases, and hallucination traps.
- You iterated prompt/tool behavior based on failures.
- Reliability improved through measurement, not intuition.

## Backup line if cloud model fails

If provider auth/network fails, the API automatically returns a deterministic fallback response grounded in local retrieval.
This keeps the demo running and still shows guardrails.
