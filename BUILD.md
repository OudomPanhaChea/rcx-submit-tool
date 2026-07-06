# Packaging RCX Submit Assistant into a downloadable app

This turns the tool into a folder your users **unzip and double-click** — no Python,
no PowerShell, no `pip install`. It works on Windows and macOS.

> **Why a folder, not a single .exe?** This app drives a real Chromium browser
> (Playwright). Bundling that into one file is unreliable. A "onedir" folder that
> includes the browser next to the app is the robust, standard approach.

---

## The one rule you can't get around

**You cannot build a Mac app on Windows, or a Windows app on a Mac.** PyInstaller is
not a cross-compiler. You have three ways to get both:

1. **GitHub Actions (recommended).** Free Windows + Mac runners build both for you.
   You never need to own a Mac. See ["Automated builds"](#automated-builds-recommended).
2. Build on Windows yourself, and borrow/rent a Mac for the Mac build.
3. Ship the source + a setup script instead of a compiled app (simplest, but users
   must install Python once).

---

## Automated builds (recommended)

The workflow at `.github/workflows/build.yml` already does everything: installs deps,
runs PyInstaller, bundles Chromium, and zips a Windows and a macOS build.

1. Push this repo to GitHub.
2. Create a release tag:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
   (Or go to the repo's **Actions** tab and run "Build apps" manually.)
3. When it finishes, download the two zips from the run's **Artifacts** section:
   `RCX-Submit-Assistant-windows.zip` and `RCX-Submit-Assistant-macos-arm64.zip`.
4. Hand those zips to your users. Done.

To also target **Intel Macs**, add a `macos-13` entry to the matrix in the workflow.

---

## Building the Windows app (one click)

Just **double-click `build-windows.bat`**. It installs everything, builds the app,
bundles the browser, and produces the file you send people:

```
dist\RCX-Submit-Assistant-windows.zip
```

(The only requirement is Python installed once on your build PC — the script tells you
if it's missing. Your *users* do NOT need Python.)

### Manual version, if you prefer

```bash
pip install -r requirements.txt pyinstaller
pyinstaller build.spec
# then bundle Chromium into the built folder:
#   Windows PowerShell:
$env:PLAYWRIGHT_BROWSERS_PATH = "$PWD\dist\RCX-Submit-Assistant\ms-playwright"
python -m playwright install chromium
# then zip dist\RCX-Submit-Assistant and distribute it.
```

---

## What your users do (zero setup, no files to edit)

1. Unzip the folder anywhere.
2. Open the `RCX-Submit-Assistant` folder and double-click **RCX-Submit-Assistant.exe**.
   A small console window opens and the dashboard opens in their browser at
   `http://127.0.0.1:5000`.
3. In **Settings**, paste their own AI API key — it's saved in their browser, so they
   only do this once. **No `.env` file, no config editing.** (Don't ship your own key.)
4. Log in → Crawl → Generate. Closing the console window quits the app.

Their login session and crawled cases are saved in a `data/` folder next to the app, so
they persist between runs.

---

## Two warnings you'll hit (and how to handle them)

- **Windows SmartScreen** ("Windows protected your PC"): unsigned apps show this. Users
  click *More info → Run anyway*. To remove it, buy a code-signing certificate (~$100+/yr).
- **macOS Gatekeeper** ("app can't be opened because it's from an unidentified
  developer"): users right-click the app → *Open* → *Open*. To remove it, you need an
  Apple Developer account ($99/yr) to sign and notarize.

For a small, trusted user group, telling them to click through is fine.

---

## Code changes already made for packaging

- `main.py` — single entry point; starts the server and opens the browser, and also
  acts as the crawler when the frozen app re-invokes itself (`login`/`crawl`).
- `config.py` — when frozen, reads templates from the bundle but keeps `data/` and
  `.env` **next to the executable** so they survive between runs.
- `app.py` — points Flask at the bundled templates and calls the crawler correctly
  whether running from source or frozen.

All of these stay backward-compatible: `python app.py` and `python main.py` still work
for development.
