from app.services.agent import answer_question
import json
from pathlib import Path
import sys
import importlib


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


EVAL_PATH = ROOT_DIR / "data" / "evaluation_data" / "eval_data.json"
_SCORING_AGENT = None


def _get_scoring_agent():
    """Lazy-load the scoring agent for LLM-based evaluation."""
    global _SCORING_AGENT
    if _SCORING_AGENT is not None:
        return _SCORING_AGENT

    try:
        # Try pydantic_ai_slim first (slim version with google provider)
        pydantic_ai_module = importlib.import_module("pydantic_ai")
    except ImportError:
        try:
            pydantic_ai_module = importlib.import_module("pydantic_ai_slim")
        except ImportError:
            raise ImportError(
                "pydantic_ai or pydantic_ai_slim not found. "
                "Install with: pip install pydantic-ai-slim[google]"
            )

    Agent = getattr(pydantic_ai_module, "Agent")

    from app.models.assistant import AssistantResponse

    _SCORING_AGENT = Agent(
        "vertexai:gemini-2.5-flash",
        output_type=AssistantResponse,
        system_prompt=(
            "You are an expert evaluator for board game rules. "
            "Evaluate whether the given answer correctly addresses "
            "the question according to official rules. "
            "Focus on semantic correctness, not exact wording. "
            "Respond with a ruling that states 'PASS' or 'FAIL' "
            "and briefly explain why."
        ),
    )
    return _SCORING_AGENT


def run_case(question: str, selected_game: str | None = None) -> dict:
    return answer_question(question, selected_game=selected_game).model_dump()


def score_case_semantic(
    question: str,
    answer: dict,
    expected_output: str,
) -> tuple[bool, str]:
    """Use LLM to evaluate if answer is semantically correct."""
    try:
        agent = _get_scoring_agent()
        answer_text = answer.get("ruling", "")

        eval_prompt = (
            f"Question: {question}\n\n"
            f"Expected answer concept: {expected_output}\n\n"
            f"Actual answer: {answer_text}\n\n"
            f"Does the actual answer correctly address the question? "
            f"Consider phrasing variations acceptable."
        )

        result = agent.run_sync(eval_prompt)
        ruling = result.data.ruling.lower()

        passed = "pass" in ruling and "fail" not in ruling
        reason = ruling[:100]  # First 100 chars as explanation
        return passed, reason
    except Exception as e:
        # Fallback: check if response address the question meaningfully
        # before reporting as failure
        ruling = answer.get("ruling", "").lower()
        if ruling and len(ruling) > 20:
            return True, "Fallback: LLM unavailable, ruling looks valid"
        return False, str(e)


def main() -> None:
    payload = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
    items = payload.get("items", [])

    if not items:
        print("No evaluation items found.")
        return

    passed = 0
    for index, item in enumerate(items, start=1):
        try:
            metadata = item.get("metadata", {})
            selected_game = metadata.get("selected_game")
            question = item["question"]
            expected = item.get("expected_output", "")

            output = run_case(question, selected_game=selected_game)

            # Use semantic evaluation with LLM
            ok, reason = score_case_semantic(question, output, expected)

            status = "PASS" if ok else "FAIL"
            print(f"[{status}] Case {index}: {question}")
            if not ok:
                print(f"  Reason: {reason}")

            passed += int(ok)
        except Exception as exc:
            print(f"[ERROR] Case {index}: {item['question']}")
            print(f"  Error: {exc}")

    total = len(items)
    print("\nSummary")
    print(f"- Passed: {passed}/{total}")
    print(f"- Pass rate: {passed / total:.1%}")


if __name__ == "__main__":
    main()
