"""Generate a unique appeal message per case, across multiple AI providers.

Supported providers (set AI_PROVIDER in .env, or pick in the dashboard):
  gemini    - Google Gemini (free tier)         needs GEMINI_API_KEY
  groq      - Groq / Llama (free tier)           needs GROQ_API_KEY
  ollama    - local model via Ollama (free)      no key, needs Ollama running
  anthropic - Claude                             needs ANTHROPIC_API_KEY
"""
import random
import time

import requests

from config import (
    GEMINI_API_KEY, GROQ_API_KEY, OPENAI_API_KEY, DEEPSEEK_API_KEY,
    ANTHROPIC_API_KEY, OLLAMA_HOST, PROVIDER_DEFAULTS,
)

# A few of the user's real past submissions, used only to steer tone/style.
REFERENCES = """\
Dear TikTok Team,
My account was recently banned without any prior warning, and I'm unable to submit an appeal. Please kindly review and restore my account.

Dear TikTok Support,
I respectfully request the restoration of my account. I was not given a chance to appeal because the notification pop-up does not include an appeal option. Please investigate this issue and review my account manually. Thank you for your assistance.

Dear TikTok Support Team,
I am contacting you regarding the sudden suspension of my account. I always strive to follow TikTok's Community Guidelines, and I believe this ban may have been an error. Furthermore, a technical glitch is preventing me from appealing natively; the restriction pop-up does not include an appeal button. I respectfully request a manual investigation into both this interface error and my account standing.

Dear TikTok Team,
I need help appealing my account. I'm having trouble using the app's appeal process. Could you please help me get my account unbanned? Thank you.
"""

SYSTEM_PROMPT = f"""You write short, polite account-support messages for the \
"Additional details" box of a platform's "Report a problem" / feedback form \
(e.g. TikTok's report feedback form). You are drafting on behalf of the account \
owner, in the first person.

Here are examples of the style and tone to match:
{REFERENCES}

Write like a REAL everyday person, not like an AI or a corporate letter.
Aim for messages that read as if a normal user typed them quickly and sincerely.

Rules for every message you write:
- Write as the account owner (first person), politely and sincerely.
- Explain the account was restricted (banned / suspended / warned / disabled)
  and that they cannot appeal from within the app because the notification /
  pop-up does not offer an appeal option, so they are reaching out directly.
- Politely ask for a manual review and to have the account restored.
- Sound HUMAN: use plain, simple, everyday words. Vary sentence length. It is
  fine to sound a little emotional, worried, or hopeful, the way a real user
  would. Do not sound stiff, formal, or templated.
- Make each message genuinely UNIQUE — vary the opening, the wording, the
  structure, and the closing. Do NOT reuse the same sentence skeleton or the
  same phrases across messages (avoid repeating lines like "I always strive to
  follow the Community Guidelines").
- Vary the greeting naturally: e.g. "Dear TikTok Team", "Hello TikTok Support",
  "Hi", or sometimes no greeting at all. Vary the length a little.
- KEEP IT SHORT: 40 to 75 words, and NEVER more than 80. A few short sentences,
  not a wall of text. At least 50 characters. No markdown, no bullet points.
- Use simple, everyday vocabulary — the way a normal person would actually type
  to support. Avoid formal, fancy, or flowery words and long run-on sentences.
- If account linking info is provided (a linked email, phone number, or a
  connected account like Facebook/Telegram), weave in ONE or TWO of the most
  relevant items in a natural sentence to help verify ownership — e.g. "the
  account is linked to the email ... and phone ...". If none is provided, do
  not invent any. NEVER include passwords.
- Do NOT include placeholder brackets like [Your Name] or [Your Username], and
  do NOT sign off with a name.
- Naturally reference the account handle when one is provided.
- Adapt to the platform and issue named in the case type (TikTok vs Instagram;
  ban vs suspension vs warning vs disabled).
- Output ONLY the message text — no preamble, no quotes, no explanation."""


def resolve_model(provider, model):
    return (model or "").strip() or PROVIDER_DEFAULTS.get(provider, "")


def provider_ready(provider, api_key=None):
    """Return (ready, missing_env_var_name). api_key (from the UI) counts too."""
    key = (api_key or "").strip()
    if provider == "gemini":
        return bool(key or GEMINI_API_KEY), "GEMINI_API_KEY"
    if provider == "groq":
        return bool(key or GROQ_API_KEY), "GROQ_API_KEY"
    if provider == "openai":
        return bool(key or OPENAI_API_KEY), "OPENAI_API_KEY"
    if provider == "deepseek":
        return bool(key or DEEPSEEK_API_KEY), "DEEPSEEK_API_KEY"
    if provider == "anthropic":
        return bool(key or ANTHROPIC_API_KEY), "ANTHROPIC_API_KEY"
    if provider == "ollama":
        return True, ""  # local, no key required
    return False, "AI_PROVIDER"


# Randomized style knobs — each message is pushed into a different shape so the
# output doesn't collapse into one template (especially on Groq/Llama).
_TONES = [
    "calm and polite", "warm and sincere", "a little worried but respectful",
    "hopeful and friendly", "plain and matter-of-fact",
    "earnest, like a first-time user", "tired but still polite",
    "grateful and cooperative",
]
_GREETINGS = [
    'open with "Dear TikTok Team,"', 'open with "Hello TikTok Support,"',
    'open with "Hi there,"', 'open with a simple "Hello,"',
    'open with "To the TikTok team,"', "start straight into the problem with no greeting",
]
_LENGTHS = [
    "very short: 2 sentences", "very short: 2-3 sentences",
    "short: 3 sentences", "short: 3-4 sentences",
]
_OPENERS = [
    "start by stating the account was restricted",
    "start by describing how you felt when it happened",
    "start by politely asking for help first, then explain",
    "start by mentioning you rely on this account and it matters to you",
]
_EXTRAS = [
    "briefly say you believe it was a mistake",
    "briefly say you always tried to follow the rules",
    "briefly mention the account matters to you (work / audience / customers)",
    "add no extra justification — keep it simple and direct",
]
_CLOSERS = [
    "end with a short thank-you", "end by asking them to review and restore it",
    "end with a hopeful line", 'end simply with "Thank you."',
    "end by saying you are happy to verify ownership",
]


def _style_directive():
    return "\n".join([
        f"- Tone: {random.choice(_TONES)}.",
        f"- Greeting: {random.choice(_GREETINGS)}.",
        f"- Length: {random.choice(_LENGTHS)}.",
        f"- Opening: {random.choice(_OPENERS)}.",
        f"- Middle: {random.choice(_EXTRAS)}.",
        f"- Ending: {random.choice(_CLOSERS)}.",
        "- Express the 'I can't appeal inside the app' idea in fresh words — never a stock phrase.",
    ])


def _user_prompt(username, project_type, contact_summary=""):
    lines = [
        "Write ONE appeal message that follows the style directive below exactly.",
        f"Account handle: @{username}",
        f"Case type: {project_type}",
    ]
    if contact_summary:
        lines.append(f"Account linking info (reference the relevant parts naturally): {contact_summary}")
    lines.append("Style for THIS specific message (make it clearly different from other messages):")
    lines.append(_style_directive())
    lines.append(f"Randomness seed: {random.randint(100000, 999999)}")
    return "\n".join(lines)


def generate_message(provider, model, username, project_type, contact_summary="", api_key=None):
    model = resolve_model(provider, model)
    prompt = _user_prompt(username, project_type, contact_summary)
    key = (api_key or "").strip()
    if provider == "gemini":
        return _gemini(model, prompt, key or GEMINI_API_KEY)
    if provider == "groq":
        return _groq(model, prompt, key or GROQ_API_KEY)
    if provider == "openai":
        return _openai(model, prompt, key or OPENAI_API_KEY)
    if provider == "deepseek":
        return _deepseek(model, prompt, key or DEEPSEEK_API_KEY)
    if provider == "ollama":
        return _ollama(model, prompt)
    if provider == "anthropic":
        return _anthropic(model, prompt, key or ANTHROPIC_API_KEY)
    raise RuntimeError(f"Unknown AI provider: {provider}")


def generate_with_fallback(order, keys, model, primary, username, project_type, contact_summary=""):
    """Try providers in `order`; on failure (rate limit, error) move to the next.

    `keys` is {provider: api_key}. Returns (text, provider_used). The configured
    `model` is only applied to the `primary` provider; fallbacks use their default.
    """
    errors = []
    for prov in order:
        key = (keys.get(prov) or "").strip()
        ready, _ = provider_ready(prov, key)
        if not ready:
            continue
        use_model = model if prov == primary else ""
        try:
            text = generate_message(prov, use_model, username, project_type, contact_summary, key)
            return text, prov
        except Exception as exc:
            errors.append(f"{prov}: {exc}")
    raise RuntimeError(" | ".join(errors) or "No configured provider available.")


def _post_with_retry(url, attempts=4, **kwargs):
    """POST that retries on rate limits (429) and server errors (5xx)."""
    resp = None
    for i in range(attempts):
        resp = requests.post(url, timeout=60, **kwargs)
        if resp.status_code < 400:
            return resp
        if resp.status_code == 429 or resp.status_code >= 500:
            wait = 3 * (i + 1)
            retry_after = resp.headers.get("Retry-After")
            if retry_after and str(retry_after).isdigit():
                wait = min(int(retry_after), 40)
            time.sleep(wait)
            continue
        break  # other 4xx errors won't be fixed by retrying
    return resp


def _gemini(model, prompt, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    gen_config = {"maxOutputTokens": 512, "temperature": 1.05, "topP": 0.92}
    # Gemini 2.5 models "think" and can burn the whole output budget, returning
    # empty text. Turn thinking off so short messages come back reliably.
    if "2.5" in model:
        gen_config["thinkingConfig"] = {"thinkingBudget": 0}
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": gen_config,
    }
    for _ in range(3):
        r = _post_with_retry(url, params={"key": api_key}, json=body)
        if r.status_code >= 400:
            raise RuntimeError(f"Gemini error {r.status_code}: {r.text[:300]}")
        cands = r.json().get("candidates", [])
        parts = cands[0].get("content", {}).get("parts", []) if cands else []
        text = "".join(p.get("text", "") for p in parts).strip()
        if text:
            return text
        time.sleep(1.5)
    raise RuntimeError("Gemini kept returning empty text. Try model 'gemini-2.0-flash'.")


def _chat_completions(url, label, model, prompt, api_key):
    """Shared caller for OpenAI-compatible chat APIs (Groq, OpenAI, DeepSeek)."""
    headers = {"Authorization": f"Bearer {api_key}"}
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 220,
        "temperature": 1.0,
        "top_p": 0.92,
        "frequency_penalty": 0.3,
        "presence_penalty": 0.2,
    }
    r = _post_with_retry(url, headers=headers, json=body)
    if r.status_code >= 400:
        raise RuntimeError(f"{label} error {r.status_code}: {r.text[:300]}")
    return r.json()["choices"][0]["message"]["content"].strip()


def _groq(model, prompt, api_key):
    return _chat_completions("https://api.groq.com/openai/v1/chat/completions",
                             "Groq", model, prompt, api_key)


def _openai(model, prompt, api_key):
    return _chat_completions("https://api.openai.com/v1/chat/completions",
                             "OpenAI", model, prompt, api_key)


def _deepseek(model, prompt, api_key):
    return _chat_completions("https://api.deepseek.com/v1/chat/completions",
                             "DeepSeek", model, prompt, api_key)


def _ollama(model, prompt):
    url = f"{OLLAMA_HOST}/api/chat"
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": {"temperature": 1.0},
    }
    try:
        r = requests.post(url, json=body, timeout=120)
    except requests.exceptions.ConnectionError:
        raise RuntimeError(f"Could not reach Ollama at {OLLAMA_HOST}. Is it running?")
    if r.status_code >= 400:
        raise RuntimeError(f"Ollama error {r.status_code}: {r.text[:300]}")
    return r.json()["message"]["content"].strip()


def _anthropic(model, prompt, api_key):
    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=model,
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()
