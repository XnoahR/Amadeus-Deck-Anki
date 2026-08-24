"""Say when a newer version is out.

Anki updates add-ons it installed from AnkiWeb. This one arrives as a file, so
without this nobody would hear about a new version unless they went and looked
at GitHub -- which nobody does.

The version comes from the /releases/latest redirect rather than GitHub's API.
The API is the obvious route and the wrong one: it allows 60 unauthenticated
calls an hour counted per IP address, and behind a shared one -- a phone
network, a campus, a CDN -- that budget is routinely already spent by strangers
before the add-on ever asks.
"""

import os
import re
import time
import urllib.request

from aqt import mw
from aqt.utils import tooltip

VERSION = "1.3.1"
REPO = "XnoahR/Amadeus-Deck-Anki"
RELEASES = "https://github.com/%s/releases/latest" % REPO

HERE = os.path.dirname(os.path.abspath(__file__))
STAMP = os.path.join(HERE, "user_files", "lastcheck")


def _ask():
    try:
        req = urllib.request.Request(
            RELEASES, method="HEAD",
            headers={"User-Agent": "AmadeusDeck/%s" % VERSION})
        with urllib.request.urlopen(req, timeout=10) as resp:
            final = resp.geturl()
    except Exception:
        return None
    try:
        os.makedirs(os.path.dirname(STAMP), exist_ok=True)
        open(STAMP, "w").close()
    except OSError:
        pass
    found = re.search(r"/tag/v?([0-9]+(?:\.[0-9]+)*)", final or "")
    return found.group(1) if found else None


def _newer(candidate, current):
    """Numeric compare, so 1.10.0 beats 1.9.0 -- string order gets that wrong."""
    try:
        return ([int(x) for x in candidate.split(".")]
                > [int(x) for x in current.split(".")])
    except (AttributeError, ValueError):
        return False


def check(config):
    """Once a day, in the background, silent unless there is news."""
    if not config.get("check_updates", True):
        return
    try:
        if time.time() - os.path.getmtime(STAMP) < 86400:
            return
    except OSError:
        pass

    def done(fut):
        try:
            found = fut.result()
        except Exception:
            return
        if found and _newer(found, VERSION):
            tooltip("Amadeus Deck %s sudah keluar (kamu pakai %s)"
                    % (found, VERSION), period=8000)

    try:
        mw.taskman.run_in_background(_ask, done)
    except Exception:
        pass
