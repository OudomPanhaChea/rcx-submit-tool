# RCX Submit Assistant

A local tool that speeds up your daily TikTok/IG account-support submissions.

It:
1. **Crawls** your own project system at `sys.rcx18.com/projects` (you log in once
   in a real browser; the session is saved and reused).
2. Pulls the account **username** (`@...`) and case type from each project card.
3. **Generates a unique "Additional details" message** per case with the Claude API,
   styled after your past submissions.
4. Computes the **rotating contact email** (`base+1@`, `base+2@`, ...).
5. Shows everything on a local dashboard with **copy buttons** — you paste into the
   TikTok "Report a problem" form and submit yourself.

It does **not** auto-submit anything to TikTok. You stay in control of every submission.

---

## Setup (one time)

Requires Python 3.9+.

```bash
cd "E:\RCX\RCX submit bot"

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
python -m playwright install chromium
```

Create your config file:

```bash
copy .env.example .env
```

Then edit `.env` and set at least:
- `AI_PROVIDER` — `gemini` (free, recommended), `groq`, `ollama`, or `anthropic`
- the matching key for that provider — e.g. `GEMINI_API_KEY` (free, see below)
- `EMAIL_BASE` — the local part of your Gmail (e.g. `abcd` for `abcd@gmail.com`)
- `START_INDEX` — the first number in the email rotation (e.g. `1`)

### Getting a free Gemini key (recommended)

1. Go to https://aistudio.google.com/apikey and sign in with a Google account.
2. Click **Create API key** (create in a new or existing project). No billing needed.
3. Copy the key (starts with `AIza...`).
4. In `.env` set `AI_PROVIDER=gemini` and `GEMINI_API_KEY=AIza...`.

Free alternatives: **Groq** — get a key at https://console.groq.com/keys and set
`AI_PROVIDER=groq` + `GROQ_API_KEY=...`. **Ollama** — install from https://ollama.com,
run `ollama pull llama3.1`, set `AI_PROVIDER=ollama` (no key). You can also switch
provider anytime from the dashboard's Settings panel.

---

## Daily use

```bash
.venv\Scripts\activate
python app.py
```

Open http://127.0.0.1:5000 in your browser, then:

1. **Log in to system** — opens a browser window; log into `sys.rcx18.com`.
   The session is saved, so you normally do this only when it expires.
2. **Crawl projects** — scrapes your current cases into the dashboard.
3. **Generate all messages** — writes a fresh, unique message for every case.
   (Use **Regenerate** on a single case for a new variation.)
4. For each case, use the **Copy** buttons for Username, Contact email, and
   Additional details, and paste them into the TikTok form:
   https://www.tiktok.com/legal/report/feedback

Run **Generate all** again each day to get new, unique messages.

---

## The email rotation

Email is built as:

```
{EMAIL_BASE}+{number}@{EMAIL_DOMAIN}      number = START_INDEX + case position
```

With `EMAIL_BASE=abcd`, `START_INDEX=1`: `abcd+1@gmail.com`, `abcd+2@gmail.com`, ...
Change any of these in the **Settings** panel (or `.env`) and click **Save settings**.
Case position is fixed at crawl time, so each case keeps a stable email.

---

## Notes

- **Provider / cost:** default is Google **Gemini** (free tier). Free tiers have
  per-minute rate limits, so "Generate all" paces itself (~1.2s between cases).
  You can change provider/model anytime in the Settings panel or `.env`.
- **Your data** (saved login session, crawled cases, generated messages) lives in
  the `data/` folder. Do not share it — `data/auth.json` contains your login session.
- If the site layout changes and crawling misses cases, `data/last_page.html` holds
  the last crawled page so the selectors can be tuned.
