# Randy (Workshop Plan)

## 1) Refined Idea

Build **Randy**, a board game rules referee agent for 2 games.
- UNO
- Werewolves of Miller's Hollow

What it does:
- Answers "what happens now?" questions from real game situations.
- Explains card/item/role effects and timing.
- Gives short, practical rulings with references to rule text.

What it does **not** do in v1:
- No image understanding.
- No full strategy coaching.
- No support for custom house rules (unless user explicitly marks them).

Why this is on-topic for AI agents:
- It must choose actions (retrieve relevant rule sections, compare conflict cases, answer with evidence).
- It uses tools + reasoning, not just one-shot text generation.

---

## 2) Keep It Small (Two-Day Scope)

### MVP boundary
- Input: plain text user question (no images).
- Output: concise ruling + cited rule snippets.
- Data source: local markdown files in `data/`.

### Optional stretch goal
- Add "house rule mode" toggle per game.

---

## 3) Minimal Agent Design

### Agent role
System behavior:
- First classify game + intent (setup, turn legality, effect resolution, edge case).
- Retrieve relevant sections only.
- If rules are ambiguous or not found, say so clearly.
- Never invent rule text.

### Tools (simple)
1. `list_games()` -> returns available games.
2. `retrieve_rules(game, query)` -> returns top matching chunks from that game's markdown.
3. `quote_rule(game, section_id)` -> returns exact snippet for citation.
4. `answer_format()` (internal template) -> forces consistent output shape.

### Response template
- Ruling: one paragraph.
- Why: 2-4 bullets.
- Citation(s): quoted lines/sections.
- "If this is a house rule, tell me and I can adapt."

---

## 4) Image Challenge Decision

Do **not** do image/card recognition in workshop MVP.

Practical workaround:
- Ask user to type card name or short description.
- Maintain a small synonym map (e.g., `+4`, `draw four`, `wild draw four`).

This keeps risk low and still demonstrates agent behavior.

---

## 5) Two-Day Build Plan

## Day 1 (Build)
1. Reuse workshop skeleton from `agent/` into `myagent/` structure.
2. Replace retail tools with rules tools.
3. Load and chunk 3 markdown rule files.
4. Implement retrieval (keyword or embedding-lite, whichever is faster in your setup).
5. Create API endpoint (`/chat`) and return structured response.
6. Add 10-15 seed test questions manually.

Definition of done Day 1:
- Agent answers correctly for common scenarios in both games.
- Responses include citations.

## Day 2 (Evaluation + polish)
1. Build `eval_data.json` with 25-40 cases.
2. Add expected tool call trajectories.
3. Run evaluation pipeline (answer relevancy + tool calling accuracy).
4. Inspect worst failures and patch system prompt/tool logic.
5. Re-run and capture before/after metrics.
6. Prepare demo script + question answers.

Definition of done Day 2:
- Measurable improvement after at least one iteration.
- Clear story: "what failed, what changed, what improved".

---

## 6) Evaluation Dataset Blueprint

Each sample should include:
- `question`
- `expected_output` (concise target behavior)

Suggested categories:
- Basic rules retrieval
- Timing/order of effects
- Illegal move detection
- Ambiguity handling (must say "unclear")
- Hallucination traps (fake card names)

Example:

```json
{
  "question": "In UNO, can I stack a +2 on a +2?",
  "expected_output": "Official UNO rules do not allow stacking..."
}
```

---

## 7) Draft Answers For Workshop Questions

### What problem does your agent solve?
Players struggle to quickly resolve rule disputes during live games, especially with long rulebooks and edge cases. The agent gives fast, cited rulings.

### Why does this problem require an agent and not any other approach?
A static FAQ cannot cover combinational game states and follow-up clarification. An agent can interpret context, retrieve relevant rules, and explain consequences interactively.

### What specific tools or external APIs does your agent rely on to take action?
Core tools are local rule retrieval and citation tools (`retrieve_rules`, `quote_rule`). Optional infrastructure: FastAPI endpoint, Langfuse tracing, and DeepEval metrics for evaluation.

### What was the hardest part about designing the prompt or the system instructions for this specific use case?
Preventing confident hallucinations when rules are missing or ambiguous. The prompt had to force uncertainty behavior and citations.

### What guardrails did you put in place to handle errors, unexpected inputs, or hallucinations?
- Mandatory citation requirement.
- Explicit "not found/unclear" fallback.
- Game classification before answering.
- Tool-first policy (retrieve before explain).
- Reject unsupported image input in MVP and request text description.

### How do you define and measure "success" for this specific agent?
- Correctness on benchmark scenarios.
- Answer relevancy score.
- Tool-calling accuracy.
- Hallucination rate (answers without valid citation).

### How did testing and evaluating your agent change your initial design or prompts?
Evaluation revealed overconfident answers and weak citations. I tightened the prompt to require evidence and added explicit ambiguity handling.

### What specific test or metric revealed the biggest flaw in your early prototype?
Tool-calling accuracy exposed that the model sometimes answered from prior knowledge without retrieving the local rule source.

### Did you discover any unexpected behaviors during evaluation, and how did you fix them?
Yes. The model mixed house rules with official rules for UNO. I fixed it by hard-prioritizing official text and adding a house-rule clarification step.

### How did an evaluation-driven approach increase trust in this agent's reliability?
It replaced intuition with measurable evidence. Iterative runs showed improved consistency, fewer uncited claims, and better handling of edge cases.

---

## 8) Demo Script (5 minutes)

1. Ask a simple question (UNO action card).
2. Ask a tricky edge case (UNO +4 challenge or Werewolves Little Girl timing).
3. Ask a fake/nonexistent card to show safe fallback.
4. Show one evaluation result before fix vs after fix.

---

## 9) Risk Control

Top risks:
- Ambiguous rules across editions.
- Agent sounding certain without evidence.
- Scope creep (image support, too many games).

Mitigation:
- Freeze to 2 games.
- Require citations in every answer.
- Keep image support out of MVP.
- Timebox Day 2 improvements to top 2 failure modes only.
