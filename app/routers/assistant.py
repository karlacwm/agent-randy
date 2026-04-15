from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.agent import answer_question

router = APIRouter(prefix="/assistant")

chat_sessions: dict[str, list[str]] = {}


class UserQuery(BaseModel):
    session_id: str
    prompt: str
    game: str | None = None


@router.get("/welcome/{session_id}")
async def welcome_message(session_id: str):
    chat_sessions[session_id] = []
    return {
        "session_id": session_id,
        "message": (
            "Welcome to Randy. Everyone needs a Randy to play boardgame with. "
            "Tell me your game and the exact situation, and I will provide a cited ruling."
        ),
    }


@router.post("/ask")
async def ask_assistant(query: UserQuery):
    prompt = query.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

    history = chat_sessions.get(query.session_id, [])
    history.append(prompt)
    # Keep only the latest prompts per session to avoid unbounded memory growth.
    chat_sessions[query.session_id] = history[-20:]

    try:
        return answer_question(prompt, selected_game=query.game)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unexpected server error while processing rules request. "
                "Try a simpler prompt with explicit game name and action."
            ),
        ) from exc
