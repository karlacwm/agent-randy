import json
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.routers.assistant import router

load_dotenv()


def _load_eval_questions() -> dict[str, list[str]]:
    eval_data_path = Path(__file__).resolve(
    ).parents[1] / "data" / "evaluation_data" / "eval_data.json"
    questions_by_game: dict[str, list[str]] = {
        "all": [],
        "uno": [],
        "werewolves": [],
    }

    try:
        payload = json.loads(eval_data_path.read_text(encoding="utf-8"))
        items = payload.get("items", [])
        seen: set[str] = set()

        for item in items:
            question = (item.get("question") or "").strip()
            metadata = item.get("metadata") or {}
            game = (metadata.get("game") or "").strip().lower()

            if not question or question in seen:
                continue

            seen.add(question)
            questions_by_game["all"].append(question)

            if game in questions_by_game:
                questions_by_game[game].append(question)
    except Exception:
        return questions_by_game

    return questions_by_game


EVAL_QUESTIONS_BY_GAME = _load_eval_questions()

app = FastAPI(title="Randy")
app.include_router(router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def home_page() -> str:
    html = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Randy</title>
    <style>
      :root {
        --butter: #fff7e6;
        --ink: #2e2a33;
        --sky: #b8dcff;
        --mint: #c9f7e8;
        --jam: #4a3856;
        --paper: rgba(255, 255, 255, 0.84);
        --line: rgba(88, 58, 42, 0.18);
        --shadow: rgba(78, 54, 46, 0.16);
        --reading-font: "Trebuchet MS", "Avenir Next", "Segoe UI", sans-serif;
      }

      * { box-sizing: border-box; }

      body {
        margin: 0;
        font-family: var(--reading-font);
        color: var(--ink);
        background:
          radial-gradient(1000px 520px at -10% -10%, var(--mint), transparent 60%),
          radial-gradient(960px 480px at 110% 0%, var(--sky), transparent 57%),
          radial-gradient(640px 400px at 40% 120%, #ffd8c2, transparent 55%),
          linear-gradient(160deg, var(--butter), #fffdf9 58%);
        min-height: 100vh;
      }

      .shell {
        width: min(980px, 100% - 28px);
        margin: 18px auto 28px;
        display: grid;
        gap: 14px;
      }

      .hero,
      .panel,
      .result-card {
        background: var(--paper);
        border: 1px solid var(--line);
        border-radius: 22px;
        box-shadow: 0 14px 30px var(--shadow);
        backdrop-filter: blur(5px);
        padding: 16px;
      }

      .hero h1 {
        margin: 0;
        font-size: clamp(1.7rem, 4vw, 2.5rem);
        color: var(--jam);
      }

      .hero p { margin: 8px 0 0; }

      .label {
        display: block;
        font-weight: 700;
        margin: 0 0 7px;
      }

      .stack {
        display: grid;
        gap: 10px;
      }

      textarea,
      input {
        width: 100%;
        border-radius: 14px;
        border: 1px solid #e4c7b1;
        background: #fffefc;
        padding: 11px 12px;
        font: inherit;
        color: var(--ink);
      }

      #prompt {
        font-family: var(--reading-font);
        font-size: 1.02rem;
        line-height: 1.6;
      }

      textarea {
        min-height: 120px;
        resize: vertical;
      }

      .game-filter {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
      }

      .faq-wrap {
        display: none;
        gap: 8px;
        flex-wrap: wrap;
      }

      .eval-wrap {
        display: none;
        margin-top: 8px;
        max-height: 220px;
        overflow: auto;
        padding: 6px;
        border: 1px dashed #dcc6b6;
        border-radius: 12px;
        background: rgba(255, 255, 255, 0.74);
      }

      .faq-wrap.visible {
        display: flex;
      }

      .eval-wrap.visible {
        display: grid;
        gap: 6px;
      }

      .filter-btn {
        border: 1px solid #e4c7b1;
        background: #fffdf8;
        color: #5a3f30;
        border-radius: 999px;
        padding: 6px 12px;
        font-size: 0.85rem;
        font-weight: 700;
        cursor: pointer;
      }

      .filter-btn.active {
        background: #ffd58e;
        border-color: #e2a98f;
      }

      .quick-btn {
        border: 1px solid #d8c8bb;
        background: #fff;
        color: #5a4639;
        border-radius: 12px;
        padding: 8px 10px;
        font-size: 0.84rem;
        text-align: left;
        cursor: pointer;
      }

      .quick-btn--compact {
        border-radius: 10px;
        font-size: 0.83rem;
      }

      .quick-btn:hover {
        background: #fff8ef;
      }

      .controls {
        margin-top: 10px;
        display: grid;
        grid-template-columns: auto;
        gap: 10px;
      }

      .button {
        border: 0;
        border-radius: 14px;
        padding: 0 18px;
        min-height: 45px;
        background: #ffd58e;
        color: #462d1f;
        font-weight: 800;
        letter-spacing: 0.01em;
        cursor: pointer;
      }

      .button.secondary {
        min-height: 36px;
        padding: 0 12px;
        border: 1px solid #e2bfaa;
        background: #fffaf4;
        color: #6a4a37;
        font-weight: 700;
      }

      .result-top {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
      }

      .card-title {
        margin: 0;
        font-size: 0.82rem;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: #755645;
      }

      .result-heading {
        font-size: 1.06rem;
        letter-spacing: 0.06em;
        margin: 0 0 14px;
      }

      .ruling {
        margin: 0;
        line-height: 1.6;
        font-family: var(--reading-font);
      }

      .details {
        margin-top: 4px;
        padding-top: 10px;
        border-top: 1px dashed #e2c8b8;
        display: grid;
        gap: 8px;
      }

      .detail-item {
        border: 1px solid #ead7cc;
        background: #fffdfa;
        border-radius: 12px;
        padding: 10px;
      }

      .detail-content {
        margin: 0;
        line-height: 1.5;
        white-space: pre-wrap;
        word-break: break-word;
      }

      .empty {
        margin: 0;
        padding: 10px;
        border: 1px dashed #dfc5b3;
        border-radius: 12px;
        background: rgba(255, 255, 255, 0.72);
      }

      @media (max-width: 680px) {
        .button { width: 100%; }
      }
    </style>
  </head>
  <body>
    <main class="shell">
      <section class="hero">
        <h1>Randy the Boardgame Companion (๑'ᵕ'๑)⸝*</h1>
        <p>-- everyone needs a friend like Randy to play boardgames with</p>
      </section>

      <section class="panel">
        <div class="stack">
          <div>
            <p class="label">Game filter (optional)</p>
            <div class="game-filter" id="game-filter">
              <button class="filter-btn active" data-game="" type="button">Auto</button>
              <button class="filter-btn" data-game="uno" type="button">UNO</button>
              <button class="filter-btn" data-game="werewolves" type="button">Werewolves</button>
            </div>
          </div>

          <div>
            <p class="label">Quick questions</p>
            <div class="faq-wrap" id="faq-wrap"></div>
          </div>

          <div>
            <button id="toggle-eval" class="button secondary" type="button">For quick copy & paste</button>
            <div class="eval-wrap" id="eval-wrap"></div>
          </div>

          <div>
            <label class="label" for="session">Session id</label>
            <input id="session" value="demo1" aria-label="Session id" />
          </div>

          <div>
            <label class="label" for="prompt">Game situation</label>
            <textarea id="prompt" placeholder="Example: Can I stack a +2 on another +2?"></textarea>
          </div>
        </div>

        <div class="controls">
          <button id="ask" class="button">Ask Randy</button>
        </div>
      </section>

      <section class="result-card" id="result">
        <p class="empty">Result appears here. Ask something to Randy first.</p>
      </section>
    </main>

    <script>
      const askBtn = document.getElementById('ask');
      const promptEl = document.getElementById('prompt');
      const sessionEl = document.getElementById('session');
      const resultEl = document.getElementById('result');
      const filterEl = document.getElementById('game-filter');
      const faqWrapEl = document.getElementById('faq-wrap');
      const evalWrapEl = document.getElementById('eval-wrap');
      const toggleEvalBtn = document.getElementById('toggle-eval');

      const EVAL_QUESTIONS_BY_GAME = __EVAL_QUESTIONS_JSON__;

      let selectedGame = '';
      let evalVisible = false;

      const FAQ_BY_GAME = {
        uno: [
          'What happens if I forget to say UNO and someone catches me before the next turn starts?',
          'Can I stack a +2 on another +2?',
          'When can I play Wild Draw Four?',
        ],
        werewolves: [
          'Can the Witch use both potions in one night?',
          'What happens if the Hunter dies?',
          'When can the Little Girl peek?',
        ],
      };

      const esc = (value) => {
        return String(value ?? '')
          .replaceAll('&', '&amp;')
          .replaceAll('<', '&lt;')
          .replaceAll('>', '&gt;')
          .replaceAll('"', '&quot;')
          .replaceAll("'", '&#39;');
      };

      const fillQuestionButtons = ({
        container,
        questions,
        className,
        emptyMessage,
        onClick,
      }) => {
        container.innerHTML = '';

        if (!questions.length) {
          if (emptyMessage) {
            const empty = document.createElement('p');
            empty.className = 'empty';
            empty.textContent = emptyMessage;
            container.appendChild(empty);
          }
          return false;
        }

        questions.forEach((question) => {
          const button = document.createElement('button');
          button.type = 'button';
          button.className = className;
          button.textContent = question;
          button.addEventListener('click', () => onClick(question));
          container.appendChild(button);
        });

        return true;
      };

      const renderFaqButtons = () => {
        const list = FAQ_BY_GAME[selectedGame] || [];

        const hasFaq = fillQuestionButtons({
          container: faqWrapEl,
          questions: list,
          className: 'quick-btn',
          onClick: (question) => {
            promptEl.value = question;
            promptEl.focus();
          },
        });

        faqWrapEl.classList.toggle('visible', hasFaq);
      };

      const getEvalQuestions = () => {
        if (selectedGame && Array.isArray(EVAL_QUESTIONS_BY_GAME[selectedGame])) {
          return EVAL_QUESTIONS_BY_GAME[selectedGame];
        }
        return EVAL_QUESTIONS_BY_GAME.all || [];
      };

      const renderEvalButtons = () => {
        fillQuestionButtons({
          container: evalWrapEl,
          questions: getEvalQuestions(),
          className: 'quick-btn quick-btn--compact',
          emptyMessage: 'No evaluation questions found.',
          onClick: async (question) => {
            promptEl.value = question;
            promptEl.focus();
            promptEl.select();
            try {
              await navigator.clipboard.writeText(question);
            } catch {
              // Clipboard permission can fail in some browsers; prompt still gets populated.
            }
          },
        });
      };

      toggleEvalBtn.addEventListener('click', () => {
        evalVisible = !evalVisible;
        evalWrapEl.classList.toggle('visible', evalVisible);
        toggleEvalBtn.textContent = evalVisible ? 'Hide questions' : 'For quick copy & paste';
      });

      filterEl.addEventListener('click', (event) => {
        const button = event.target.closest('[data-game]');
        if (!button) {
          return;
        }

        selectedGame = button.dataset.game || '';
        const buttons = filterEl.querySelectorAll('.filter-btn');
        buttons.forEach((btn) => btn.classList.remove('active'));
        button.classList.add('active');
        renderFaqButtons();
        renderEvalButtons();
      });

      renderFaqButtons();
      renderEvalButtons();

      const renderError = (message) => {
        resultEl.innerHTML = `<p class="empty">${esc(message)}</p>`;
      };

      const renderResponse = (data) => {
        const detailConfig = [
          ['source', 'Source'],
          ['evidence', 'What the rulebook says'],
          ['follow_up', 'Follow-up - need more info'],
        ];

        const fallbackByKey = {
          source: 'No source available.',
          evidence: 'No evidence quote available.',
          follow_up: 'No follow-up needed.',
        };

        const detailItems = detailConfig
          .map(([key, label]) => {
            const value = data[key] || fallbackByKey[key];
            return (
              '<div class="detail-item">'
              + `<p class="card-title">${label}</p>`
              + `<p class="detail-content">${esc(value)}</p>`
              + '</div>'
            );
          });

        const detailsContent = detailItems.join('');
        const detailsToggle = (
          '<button class="button secondary" '
          + 'id="toggle-details" type="button">'
          + 'Show details</button>'
        );
        const detailsBlock = (
          '<div class="details" id="details-block" '
          + `style="display:none;">${detailsContent}</div>`
        );

        resultEl.innerHTML = `
          <div class="result-top">
            <p class="card-title result-heading">Randy's reply</p>
          </div>
          <p class="ruling">${esc(data.ruling || 'No ruling generated.')}</p>
          ${detailsToggle}
          ${detailsBlock}
        `;

        const toggleBtn = document.getElementById('toggle-details');
        const detailsEl = document.getElementById('details-block');
        toggleBtn.addEventListener('click', () => {
          const hidden = detailsEl.style.display === 'none';
          detailsEl.style.display = hidden ? 'grid' : 'none';
          toggleBtn.textContent = hidden ? 'Hide details' : 'Show details';
        });
      };

      askBtn.addEventListener('click', async () => {
        const prompt = promptEl.value.trim();
        const sessionId = sessionEl.value.trim() || 'demo1';

        if (!prompt) {
          renderError('Please enter a prompt first.');
          return;
        }

        askBtn.disabled = true;
        askBtn.textContent = 'Randy is thinking...';
        renderError('Randy is checking the game rules...');

        try {
          const res = await fetch('/assistant/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              session_id: sessionId,
              prompt,
              game: selectedGame || null,
            }),
          });

          const data = await res.json();
          if (!res.ok) {
            renderError(data.detail || 'Request failed.');
          } else {
            renderResponse(data);
          }
        } catch {
          renderError('Request failed. Please check server logs and try again.');
        } finally {
          askBtn.disabled = false;
          askBtn.textContent = 'Ask Randy';
        }
      });
    </script>
  </body>
</html>
    """
    return html.replace("__EVAL_QUESTIONS_JSON__", json.dumps(EVAL_QUESTIONS_BY_GAME))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
