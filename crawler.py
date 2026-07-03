"""Playwright crawler for the RCX projects system.

Usage:
    python crawler.py login   # opens a browser, you log in once; session is saved
    python crawler.py crawl   # reuses the saved session, scrapes all pages +
                              # each project's detail page (linked email/phone/etc.)

Status tokens printed on the last line: LOGIN_OK / LOGIN_TIMEOUT /
CRAWL_OK <n> / NO_SESSION / SESSION_EXPIRED.
"""
import sys
import re
import time

from playwright.sync_api import sync_playwright

from config import AUTH_FILE, PROJECTS_URL, DATA_DIR, save_cases

# Read ONLY the real project-card header (`.media-title a`) + its badges + the
# link to the project detail page.
EXTRACT_JS = r"""
() => {
  const out = [];
  const seen = new Set();
  for (const node of document.querySelectorAll('.media-title')) {
    const anchor = node.querySelector('a') || node;
    const full = (anchor.textContent || '').replace(/\s+/g, ' ').trim();
    const m = full.match(/@([A-Za-z0-9._]+)/);
    if (!m) continue;
    const username = m[1];
    if (seen.has(username)) continue;
    seen.add(username);

    const card = node.parentElement || node;
    let status = '', days = '';
    const job = card.querySelector('.author-box-job');
    if (job) {
      for (const b of job.querySelectorAll('.badge')) {
        const t = b.textContent.replace(/\s+/g, ' ').trim();
        if (/Days?\s*Left/i.test(t)) days = t;
        else if (!status && !/Task|Completed/i.test(t)) status = t;
      }
    }
    out.push({
      username,
      projectType: full.split('@')[0].trim() || 'TikTok',
      title: full,
      status, days,
      href: anchor.getAttribute('href') || '',
    });
  }
  return out;
}
"""

EMAIL_RE = re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}')
PHONE_RE = re.compile(r'(?<!\d)(?:\+?\d[\d\s\-]{7,13}\d)(?!\d)')
PW_LINE_RE = re.compile(r'^\s*(password|pw|pwd|pass)\b', re.I)
SOCIALS = [
    ("Facebook", re.compile(r'(?:facebook|fb)\s*[:\-]?\s*(.+)', re.I)),
    ("Telegram", re.compile(r'telegram\s*[:\-]?\s*(.+)', re.I)),
    ("WhatsApp", re.compile(r'whatsapp\s*[:\-]?\s*(.+)', re.I)),
    ("Instagram", re.compile(r'instagram\s*[:\-]?\s*(.+)', re.I)),
    ("Line", re.compile(r'\bline\s*[:\-]?\s*(.+)', re.I)),
]


def _parse_detail(text):
    """Extract linking info from a project's description; never keep passwords."""
    if not text:
        return {"summary": "", "emails": [], "phones": []}
    kept = []
    for ln in text.splitlines():
        if PW_LINE_RE.match(ln):
            continue                       # drop password lines
        if "tiktok.com/@" in ln.lower():
            continue                       # we build the profile link ourselves
        kept.append(ln)
    clean = "\n".join(kept)

    emails, phones, socials = [], [], []
    for e in EMAIL_RE.findall(clean):
        if e not in emails:
            emails.append(e)
    for m in PHONE_RE.findall(clean):
        d = re.sub(r"\D", "", m)
        if 8 <= len(d) <= 11 and d not in phones:
            phones.append(d)
    for line in clean.splitlines():
        for label, rx in SOCIALS:
            mm = rx.search(line)
            if mm:
                val = mm.group(1).strip(" :-").strip()[:40]
                if val:
                    socials.append(f"{label}: {val}")
                break

    parts = []
    if emails:
        parts.append("Linked email: " + ", ".join(emails[:2]))
    if phones:
        parts.append("Linked phone: " + ", ".join(phones[:2]))
    parts.extend(socials[:2])
    return {"summary": " | ".join(parts), "emails": emails[:3], "phones": phones[:3]}


def _extract(page):
    try:
        return page.evaluate(EXTRACT_JS)
    except Exception:
        return []


def login():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context()
        page = ctx.new_page()
        try:
            page.goto(PROJECTS_URL, wait_until="domcontentloaded")
        except Exception:
            pass
        print(">> Log in inside the opened browser window. Waiting up to 5 minutes...",
              flush=True)

        ok = False
        deadline = time.time() + 300
        while time.time() < deadline:
            if page.query_selector("input[type=password]"):
                time.sleep(2)
                continue
            if "projects" not in page.url:
                try:
                    page.goto(PROJECTS_URL, wait_until="domcontentloaded")
                    page.wait_for_timeout(1500)
                except Exception:
                    pass
            if _extract(page):
                ok = True
                break
            time.sleep(2)

        if ok:
            ctx.storage_state(path=str(AUTH_FILE))
            browser.close()
            print("LOGIN_OK")
        else:
            browser.close()
            print("LOGIN_TIMEOUT")


def crawl():
    if not AUTH_FILE.exists():
        print("NO_SESSION")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(storage_state=str(AUTH_FILE))
        page = ctx.new_page()
        try:
            page.goto(PROJECTS_URL, wait_until="domcontentloaded")
        except Exception:
            pass
        page.wait_for_timeout(1500)

        if page.query_selector("input[type=password]"):
            browser.close()
            print("SESSION_EXPIRED")
            return

        # 1) Walk every list page via the pagination "Next" link.
        cards, seen, visited = [], set(), {PROJECTS_URL}
        for _ in range(200):
            page.wait_for_timeout(400)
            for c in _extract(page):
                if c["username"] in seen:
                    continue
                seen.add(c["username"])
                cards.append(c)
            nxt = page.query_selector('.pagination a[rel="next"]')
            href = nxt.get_attribute("href") if nxt else None
            if not href or href in visited:
                break
            visited.add(href)
            try:
                page.goto(href, wait_until="domcontentloaded")
            except Exception:
                break

        # 2) Visit each detail page for the linking info (email/phone/socials).
        for c in cards:
            detail = {"summary": "", "emails": [], "phones": []}
            if c.get("href"):
                try:
                    page.goto(c["href"], wait_until="domcontentloaded")
                    page.wait_for_timeout(300)
                    el = page.query_selector(".description-wrapper")
                    if el:
                        detail = _parse_detail(el.inner_text())
                except Exception:
                    pass
            c["contact_summary"] = detail["summary"]
            c["emails"] = detail["emails"]
            c["phones"] = detail["phones"]

        browser.close()

    cases = []
    for i, c in enumerate(cards):
        cases.append({
            "idx": i,
            "username": c["username"],
            "project_type": c.get("projectType") or "TikTok",
            "status": c.get("status", ""),
            "days_left": c.get("days", ""),
            "tiktok_url": f"https://tiktok.com/@{c['username']}",
            "contact_summary": c.get("contact_summary", ""),
            "emails": c.get("emails", []),
            "phones": c.get("phones", []),
        })
    save_cases(cases)
    print(f"CRAWL_OK {len(cases)}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "crawl"
    if cmd == "login":
        login()
    elif cmd == "crawl":
        crawl()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
