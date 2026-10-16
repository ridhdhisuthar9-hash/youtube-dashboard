"""Double-click me to start the Channel Dashboard.

Windows: double-click this file (it opens with Python). Mac / Linux: run  python3 START_WEB_APP.py

What it does:
  1. installs the libraries the first time (needs internet, a few minutes)
  2. starts the web page and opens it in your browser (http://localhost:8000)
Keep the black window open while you use the page. Close it to stop.
"""

import importlib.util
import os
import subprocess
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
sys.path.insert(0, HERE)


def wait_and_exit(code: int) -> None:
    # keep the window open so the message can be read (a window that closes at once helps nobody)
    try:
        input("\nPress Enter to close this window...")
    except EOFError:
        pass
    sys.exit(code)


def main() -> None:
    if not os.path.isdir(os.path.join(HERE, "ytdash")):
        print("The rest of the project is missing next to this file.")
        print("This usually means the file was opened from INSIDE the zip.\n")
        print("Fix: close this window, right-click the zip file, choose 'Extract All',")
        print("open the new folder, and double-click START_WEB_APP.py there.")
        wait_and_exit(1)

    if sys.version_info < (3, 9):
        print("This needs Python 3.9 or newer. Please install the latest Python from python.org.")
        wait_and_exit(1)

    missing = [m for m in ("pandas", "matplotlib", "numpy") if importlib.util.find_spec(m) is None]
    if missing:
        print("First-time setup: installing the libraries. This can take a few minutes...\n")
        code = subprocess.call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        if code != 0:
            print("\nThe libraries could not be installed. Check your internet connection and try again.")
            wait_and_exit(1)

    print("\nStarting Channel Dashboard. Your browser will open in a moment.")
    from ytdash.webapp import main as run_app

    code = run_app([])
    if code:
        wait_and_exit(code)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
    except Exception:  # noqa: BLE001 - show the problem instead of a window that vanishes
        traceback.print_exc()
        print("\nSomething went wrong (details above). Please send a photo of this window.")
        wait_and_exit(1)
