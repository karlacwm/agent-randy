from app.services.agent import answer_question
import json
from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


EVAL_PATH = ROOT_DIR / "data" / "evaluation_data" / "eval_data.json"


def run_case(question: str, selected_game: str | None = None) -> dict:
    return answer_question(question, selected_game=selected_game).model_dump()


def score_case(output: dict, must_include: list[str]) -> tuple[bool, list[str]]:
    output_text = json.dumps(output, ensure_ascii=False).lower()
    missing = [needle for needle in must_include if needle.lower()
               not in output_text]
    return len(missing) == 0, missing


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
            output = run_case(item["question"], selected_game=selected_game)
            must_include = metadata.get("must_include", [])
            ok, missing = score_case(output, must_include)

            status = "PASS" if ok else "FAIL"
            print(f"[{status}] Case {index}: {item['question']}")
            if not ok:
                print(f"  Missing signals: {missing}")

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
