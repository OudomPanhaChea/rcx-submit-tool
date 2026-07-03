"""Local dashboard: crawl cases, generate messages, copy details into the form."""
import subprocess
import sys
import time

from flask import Flask, render_template, request, jsonify

from config import (
    BASE_DIR,
    load_cases, load_state, save_state, build_email,
)
import generator

app = Flask(__name__)

CRAWLER = str(BASE_DIR / "crawler.py")
PROVIDERS = ["gemini", "groq", "deepseek", "openai", "anthropic", "ollama"]


def _is_banned(case):
    return "ban" in (case.get("project_type") or "").lower()


def _email_map(config, cases):
    """Contact email only for TikTok Banned cases; numbering counts only those."""
    out, pos = {}, 0
    for c in cases:
        if _is_banned(c):
            out[c["username"]] = build_email(config, pos)
            pos += 1
        else:
            out[c["username"]] = ""
    return out


def _run_crawler(command, timeout):
    """Run crawler.py as a subprocess and return its final status token."""
    try:
        proc = subprocess.run(
            [sys.executable, CRAWLER, command],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return "TIMEOUT", ""
    output = (proc.stdout or "").strip()
    lines = [ln for ln in output.splitlines() if ln.strip()]
    status = lines[-1] if lines else ""
    return status, output


@app.route("/")
def index():
    state = load_state()
    config = state["config"]
    messages = state["messages"]
    cases = load_cases()
    emails = _email_map(config, cases)
    for c in cases:
        c["email"] = emails.get(c["username"], "")
        c["message"] = messages.get(c["username"], "")

    ready, key_name = generator.provider_ready(config["provider"])
    return render_template(
        "index.html",
        cases=cases,
        config=config,
        providers=PROVIDERS,
        provider_ready=ready,
        missing_key=key_name,
    )


@app.route("/config", methods=["POST"])
def update_config():
    data = request.get_json(force=True)
    state = load_state()
    cfg = state["config"]

    provider = data.get("provider", cfg["provider"]).strip().lower()
    if provider in PROVIDERS:
        cfg["provider"] = provider
    cfg["model"] = data.get("model", cfg["model"]).strip()
    cfg["email_base"] = data.get("email_base", cfg["email_base"]).strip() or cfg["email_base"]
    cfg["email_domain"] = data.get("email_domain", cfg["email_domain"]).strip() or cfg["email_domain"]
    try:
        cfg["start_index"] = int(data.get("start_index", cfg["start_index"]))
    except (TypeError, ValueError):
        pass
    save_state(state)

    ready, key_name = generator.provider_ready(cfg["provider"])
    emails = _email_map(cfg, load_cases())
    return jsonify({"ok": True, "config": cfg, "emails": emails,
                    "provider_ready": ready, "missing_key": key_name})


@app.route("/login", methods=["POST"])
def login():
    status, output = _run_crawler("login", timeout=330)
    ok = status == "LOGIN_OK"
    msg = {
        "LOGIN_OK": "Logged in and session saved. You can now crawl.",
        "LOGIN_TIMEOUT": "Login window timed out before a logged-in page was detected.",
        "TIMEOUT": "Login process took too long and was stopped.",
    }.get(status, f"Login finished with: {status}")
    return jsonify({"ok": ok, "message": msg, "raw": output})


@app.route("/crawl", methods=["POST"])
def crawl():
    status, output = _run_crawler("crawl", timeout=600)
    ok = status.startswith("CRAWL_OK")
    if ok:
        count = status.split(" ", 1)[1] if " " in status else "?"
        msg = f"Crawled {count} case(s)."
    else:
        msg = {
            "NO_SESSION": "No saved session. Click 'Log in to system' first.",
            "SESSION_EXPIRED": "Session expired. Click 'Log in to system' again.",
            "TIMEOUT": "Crawl took too long and was stopped.",
        }.get(status, f"Crawl finished with: {status}")
    return jsonify({"ok": ok, "message": msg, "raw": output})


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json(force=True)
    target = data.get("username", "all")
    keys = data.get("keys") or {}
    # Backward compatible: single api_key becomes the key for the primary provider.
    single_key = data.get("api_key", "")

    state = load_state()
    provider = state["config"]["provider"]
    model = state["config"]["model"]
    if single_key and provider not in keys:
        keys[provider] = single_key

    # Fallback order: what the UI sent, else just the primary provider.
    order = [p for p in (data.get("order") or []) if p in PROVIDERS]
    if provider not in order:
        order = [provider] + order

    # At least one provider in the chain must be usable.
    if not any(generator.provider_ready(p, keys.get(p, ""))[0] for p in order):
        return jsonify({"ok": False,
                        "message": f"No usable AI provider. Add an API key for '{provider}' in Settings."}), 400

    cases = load_cases()
    if target != "all":
        cases = [c for c in cases if c["username"] == target]
    if not cases:
        return jsonify({"ok": False, "message": "No matching case to generate."}), 404

    generated = {}
    errors = []
    used = set()
    for i, c in enumerate(cases):
        try:
            text, prov = generator.generate_with_fallback(
                order, keys, model, provider,
                c["username"], c.get("project_type", "TikTok"), c.get("contact_summary", ""),
            )
            state["messages"][c["username"]] = text
            generated[c["username"]] = text
            used.add(prov)
        except Exception as exc:
            errors.append(f"@{c['username']}: {exc}")
        if target == "all" and i < len(cases) - 1:
            time.sleep(1.0)

    save_state(state)
    ok = bool(generated)
    message = f"Generated {len(generated)} message(s)."
    if used:
        message += " via " + ", ".join(sorted(used))
    if errors:
        message += f" {len(errors)} failed."
    return jsonify({"ok": ok, "message": message, "messages": generated,
                    "errors": errors, "used": sorted(used)})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
