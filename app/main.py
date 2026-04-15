from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.routers.assistant import router

load_dotenv()

app = FastAPI(title="Randy")
app.include_router(router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def home_page() -> str:
    return """
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
        --melon: #ffbfa5;
        --sky: #b8dcff;
        --mint: #c9f7e8;
        --jam: #4a3856;
        --paper: rgba(255, 255, 255, 0.84);
        --line: rgba(88, 58, 42, 0.18);
        --shadow: rgba(78, 54, 46, 0.16);
      }

      * { box-sizing: border-box; }

      body {
        margin: 0;
        font-family: "Trebuchet MS", "Avenir Next", "Segoe UI", sans-serif;
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

      .faq-wrap.visible {
        display: flex;
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

      .faq-btn {
        border: 1px solid #d8c8bb;
        background: #fff;
        color: #5a4639;
        border-radius: 12px;
        padding: 8px 10px;
        font-size: 0.84rem;
        text-align: left;
        cursor: pointer;
      }

      .faq-btn:hover {
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

      .ruling { margin: 0; line-height: 1.5; }

      .details {
        margin-top: 4px;
        padding-top: 10px;
        border-top: 1px dashed #e2c8b8;
        display: grid;
        gap: 8px;
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
            <label class="label" for="session">Session id</label>
            <input id="session" value="demo-ui" aria-label="Session id" />
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
        <p class="empty">Result appears here. Ask your first scenario above.</p>
      </section>
    </main>

    <script>
      const askBtn = document.getElementById('ask');
      const promptEl = document.getElementById('prompt');
      const sessionEl = document.getElementById('session');
      const resultEl = document.getElementById('result');
      const filterEl = document.getElementById('game-filter');
      const faqWrapEl = document.getElementById('faq-wrap');

      let selectedGame = '';

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

      const renderFaqButtons = () => {
        faqWrapEl.innerHTML = '';
        const list = FAQ_BY_GAME[selectedGame] || [];

        if (!list.length) {
          faqWrapEl.classList.remove('visible');
          return;
        }

        list.forEach((question) => {
          const button = document.createElement('button');
          button.type = 'button';
          button.className = 'faq-btn';
          button.textContent = question;
          button.addEventListener('click', () => {
            promptEl.value = question;
            promptEl.focus();
          });
          faqWrapEl.appendChild(button);
        });

        faqWrapEl.classList.add('visible');
      };

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
      });

      renderFaqButtons();

      const esc = (value) => {
        return String(value ?? '')
          .replaceAll('&', '&amp;')
          .replaceAll('<', '&lt;')
          .replaceAll('>', '&gt;')
          .replaceAll('"', '&quot;')
          .replaceAll("'", '&#39;');
      };

      const renderError = (message) => {
        resultEl.innerHTML = `<p class="empty">${esc(message)}</p>`;
      };

      const renderResponse = (data) => {
        const source = data.source ? `<p class="card-title">Source</p><p class="ruling">${esc(data.source)}</p>` : '';
        const evidence = data.evidence ? `<p class="card-title">Evidence</p><p class="ruling">${esc(data.evidence)}</p>` : '';
        const followUp = data.follow_up ? `<p class="card-title">Need More Info</p><p class="ruling">${esc(data.follow_up)}</p>` : '';
        const detailsContent = `${source}${evidence}${followUp}`;
        const hasDetails = Boolean(data.source || data.evidence || data.follow_up);
        const detailsToggle = hasDetails
          ? '<button class="button secondary" id="toggle-details" type="button">Show details</button>'
          : '';
        const detailsBlock = hasDetails
          ? `<div class="details" id="details-block" style="display:none;">${detailsContent}</div>`
          : '';

        resultEl.innerHTML = `
          <div class="result-top">
            <p class="card-title">Game rules</p>
          </div>
          <p class="ruling">${esc(data.ruling || 'No ruling generated.')}</p>
          ${detailsToggle}
          ${detailsBlock}
        `;

        if (hasDetails) {
          const toggleBtn = document.getElementById('toggle-details');
          const detailsEl = document.getElementById('details-block');
          toggleBtn.addEventListener('click', () => {
            const hidden = detailsEl.style.display === 'none';
            detailsEl.style.display = hidden ? 'grid' : 'none';
            toggleBtn.textContent = hidden ? 'Hide details' : 'Show details';
          });
        }
      };

      askBtn.addEventListener('click', async () => {
        const prompt = promptEl.value.trim();
        const sessionId = sessionEl.value.trim() || 'demo-ui';

        if (!prompt) {
          renderError('Please enter a prompt first.');
          return;
        }

        askBtn.disabled = true;
        askBtn.textContent = 'Thinking...';
        renderError('Working on your ruling...');

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
        } catch (error) {
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
