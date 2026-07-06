"""Single entry point for both the dev run and the packaged (PyInstaller) app.

Usage:
    python main.py            # start the local dashboard and open the browser
    python main.py login      # run the Playwright login flow (used internally)
    python main.py crawl       # run the crawl (used internally)

When frozen by PyInstaller, `sys.executable` is this app's binary, so app.py
re-invokes it as `<app> login` / `<app> crawl` instead of spawning python.
"""
import os
import sys
import threading
import webbrowser
from pathlib import Path

# When frozen, look for Chromium shipped next to the executable in ./ms-playwright
# (the build step installs it there). This must run before Playwright is imported.
if getattr(sys, "frozen", False):
    _browsers = Path(sys.executable).resolve().parent / "ms-playwright"
    if _browsers.exists():
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(_browsers))


def _run_crawler_cli(cmd):
    import crawler
    if cmd == "login":
        crawler.login()
    elif cmd == "crawl":
        crawler.crawl()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


def main():
    # Internal subcommands: let the frozen binary act as the crawler.
    if len(sys.argv) > 1 and sys.argv[1] in ("login", "crawl"):
        _run_crawler_cli(sys.argv[1])
        return

    from app import app

    host, port = "127.0.0.1", 5000
    url = f"http://{host}:{port}"
    # Open the browser shortly after the server starts.
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    print(f">> RCX Submit Assistant running at {url}  (close this window to quit)")
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
