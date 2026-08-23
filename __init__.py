"""
Amadeus Deck -- a companion on the Anki deck list.

Only the deck browser is touched. Card templates are never read or modified,
so whatever note-type styling you use stays exactly as it is.
"""

import html as _html
import json
import os
import time
import random
import re

from aqt import gui_hooks, mw
from aqt.deckbrowser import DeckBrowserContent

ADDON = os.path.basename(os.path.dirname(__file__))
HERE = os.path.dirname(__file__)
CHARDIR = os.path.join(HERE, "character")

# Anki serves addon files under /_addons/<package>/... once they are exported.
mw.addonManager.setWebExports(__name__, r"character/.*\.(png|jpg|jpeg|webp|gif)")

MOODS = [
    "normal", "happy", "winking", "sided_pleasant", "sided_thinking",
    "disappointed", "sad", "annoyed", "pissed", "angry", "blush",
    "sided_blush", "eyes_closed", "sided_worried", "sided_surprised",
    "indifferent", "side",
]

DEFAULT_LINES = {
    "reminder": [
        "Kamu belum review hari ini. {due} kartu menumpuk.",
        "{due} kartu masih menunggu. Aku catat lho.",
        "Mau mulai, atau mau kutagih terus?",
    ],
    "behind": [
        "Sisa {due}. Baru {done} dari {target}.",
        "Setengah jalan pun belum. Ayo.",
        "{done} dari {target}. Jangan berhenti di sini.",
    ],
    "close": [
        "Tinggal sedikit lagi. {done} dari {target}.",
        "Hampir. Selesaikan sekalian.",
    ],
    "target": [
        "Target {target} tercapai. ...Kerja bagus.",
        "Sudah {done}? Kamu serius rupanya.",
        "B-bukan berarti aku terkesan, ya.",
    ],
    "clear": [
        "Semua deck kosong. Puas?",
        "Tidak ada yang tersisa. Istirahatlah.",
        "Hari ini bersih. Bagus.",
    ],
    "broken": [
        "Streak-mu putus. Mulai lagi dari satu.",
        "Kemarin kamu tidak datang.",
        "Ya sudah. Yang penting hari ini.",
    ],
    "poke": [
        "Apa? Aku sedang menghitung.",
        "Jangan dicolek terus.",
        "...kenapa? Ada yang mau ditanya?",
        "Kerjakan kartunya, bukan aku.",
        "Hmph. Kamu bosan, ya?",
    ],
    "chatter": [
        "Sisa {due}. Aku tunggu.",
        "Kalau capek, berhenti sebentar tidak apa-apa.",
        "Menunda cuma menumpuk besok.",
        "Target hari ini {target}. Masih jauh?",
        "Jangan lupa minum.",
    ],
}

DEFAULT_MOOD_FOR = {
    "reminder": ["sided_worried", "annoyed"],
    "behind": ["normal", "indifferent", "side"],
    "close": ["sided_thinking", "normal"],
    "target": ["blush", "happy", "sided_surprised"],
    "clear": ["blush", "sided_pleasant"],
    "broken": ["sad", "disappointed"],
    "poke": ["sided_surprised", "blush", "annoyed", "sided_blush"],
    "chatter": ["normal", "indifferent", "sided_thinking", "eyes_closed", "side"],
}



DECK_CSS = {
    "vhs": """
/* Anki drives its whole look from custom properties, so redefining those is
   both cleaner and more complete than overriding rule by rule. This is what
   finally kills the default rounded panel behind the deck table. */
:root,:root.night-mode{{
  --canvas:#0d0b12;
  --canvas-glass:transparent;
  --canvas-elevated:#151020;
  --canvas-inset:#0d0b12;
  --border:#3a2b52;
  --border-subtle:#2b1f3d;
  --border-strong:#ff2d55;
  --fg:#cdc2e0;
  --fg-subtle:#7d7194;
  --fg-faint:#4b4260;
  --fg-link:#00e5ff;
  --state-new:#00e5ff;
  --state-learn:#ffb200;
  --state-review:#ff6ea1;
  --border-radius-medium:0;
  --border-radius:0;
}}
/* the table's own card would sit inside our box and read as a double frame */
.fancy table,table{{background:transparent !important;border:0 !important;
  box-shadow:none !important;border-radius:0 !important;padding:0 !important}}
tr.current td,tr:hover:not(.top-level-drag-row) td{{background:rgba(255,45,85,.14) !important}}
tr.current td:first-child{{box-shadow:inset 3px 0 0 #ff2d55}}
tr.current a.deck{{color:#fff !important}}
a.deck{{color:#e6dcf5}}
.amd-deckbox{{background:#151020;border:2px solid #2b1f3d;
  box-shadow:inset 0 0 50px rgba(255,45,85,.06)}}
.amd-deckbox::-webkit-scrollbar-thumb{{background:#3a2b52 !important;border-radius:0 !important}}
.amd-deckbox::-webkit-scrollbar-thumb:hover{{background:#ff2d55 !important}}
img.gears{{filter:invert(72%) sepia(20%) hue-rotate(215deg)}}
""",
    "holo": """
:root,:root.night-mode{{
  --canvas:#080d14;
  --canvas-glass:transparent;
  --canvas-elevated:#0f1722;
  --canvas-inset:#080d14;
  --border:#22405a;
  --border-subtle:#1d3448;
  --border-strong:#35d6ff;
  --fg:#9db6cc;
  --fg-subtle:#5c7d99;
  --fg-faint:#33495c;
  --fg-link:#35d6ff;
  --state-new:#35d6ff;
  --state-learn:#ff4fd8;
  --state-review:#7ce0b0;
  --border-radius-medium:0;
  --border-radius:0;
}}
.fancy table,table{{background:transparent !important;border:0 !important;
  box-shadow:none !important;border-radius:0 !important;padding:0 !important}}
tr.current td,tr:hover:not(.top-level-drag-row) td{{background:rgba(53,214,255,.13) !important}}
tr.current td:first-child{{box-shadow:inset 3px 0 0 #35d6ff}}
tr.current a.deck{{color:#fff !important}}
a.deck{{color:#d9e8f7}}
.amd-deckbox{{background:#0f1722;border:1px solid #1d3448;
  box-shadow:inset 0 0 50px rgba(53,214,255,.05)}}
.amd-deckbox::-webkit-scrollbar-thumb{{background:#22405a !important;border-radius:0 !important}}
.amd-deckbox::-webkit-scrollbar-thumb:hover{{background:#35d6ff !important}}
img.gears{{filter:invert(64%) sepia(30%) hue-rotate(160deg)}}
""",
}



BAR_CSS = {
    "vhs": """
body{background:#0d0b12 !important;border-top:2px solid #2b1f3d !important}
button{background:#151020 !important;color:#cdc2e0 !important;
  border:1px solid #2b1f3d !important;border-radius:0 !important;
  padding:6px 14px !important}
button:hover{background:#241a35 !important;color:#fff !important;
  border-color:#ff2d55 !important}
""",
    "holo": """
body{background:#080d14 !important;border-top:1px solid #1d3448 !important}
button{background:#0f1722 !important;color:#9db6cc !important;
  border:1px solid #1d3448 !important;border-radius:0 !important;
  padding:6px 14px !important}
button:hover{background:#16283a !important;color:#fff !important;
  border-color:#35d6ff !important}
""",
}


def conf():
    return mw.addonManager.getConfig(__name__) or {}



def _safe_fmt(text, values):
    try:
        return text.format(**values)
    except (KeyError, IndexError):
        return text


def _merged(key, fallback):
    """Config wins per state, so editing one line pool cannot wipe out the rest
    and deleting a key quietly restores the built-in."""
    out = dict(fallback)
    user = conf().get(key)
    if isinstance(user, dict):
        for state, val in user.items():
            if isinstance(val, list) and val:
                out[state] = val
    return out


def LINES_():
    return _merged("lines", DEFAULT_LINES)


def MOODS_():
    return _merged("moods", DEFAULT_MOOD_FOR)


def pictures():
    """Group the user's files by the mood their filename ends with."""
    found = {}
    if not os.path.isdir(CHARDIR):
        return found
    for name in sorted(os.listdir(CHARDIR)):
        if not name.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
            continue
        stem = os.path.splitext(name)[0]
        tail = re.sub(r"\d+$", "", stem)          # drop the trailing number
        for mood in sorted(MOODS, key=len, reverse=True):
            if tail.endswith(mood):
                found.setdefault(mood, []).append(name)
                break
    return found


def reviews_today():
    try:
        cutoff = mw.col.sched.day_cutoff
        start = (cutoff - 86400) * 1000
        return mw.col.db.scalar(
            "select count() from revlog where id >= ? and type != 4", start) or 0
    except Exception:
        return 0


def due_total():
    try:
        tree = mw.col.sched.deck_due_tree()
        return (tree.new_count or 0) + (tree.review_count or 0) + (tree.learn_count or 0)
    except Exception:
        return 0


def streak_days():
    """Consecutive days with at least one review, counting back from today.

    No lookback window: an earlier version capped the scan at 400 days and so
    reported exactly 400 to anyone with a longer run. Grouping in SQL keeps it
    cheap even over years of history."""
    try:
        cutoff = mw.col.sched.day_cutoff
        rows = mw.col.db.list(
            "select distinct cast((id/1000 - ?) / 86400 as int) from revlog "
            "where type != 4", cutoff)
        days = set(int(r) for r in rows)
        streak, step = 0, -1
        while step in days:
            streak += 1
            step -= 1
        if 0 in days:            # today already counts
            streak += 1
        return streak
    except Exception:
        return 0


def backlog():
    """Cards actually waiting, ignoring the daily limits. The deck list shows
    the limited number; this is the real pile behind it."""
    try:
        cutoff = mw.col.sched.day_cutoff
        crt = mw.col.db.scalar("select crt from col") or 0
        day = int((cutoff - crt) / 86400)
        return mw.col.db.scalar(
            "select count() from cards where queue = 2 and due <= ?", day) or 0
    except Exception:
        return 0



BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun",
         "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]



NOTES_PATH = os.path.join(HERE, "notes.json")


def history(days):
    """Reviews per day for the last N days, oldest first."""
    out = [0] * days
    try:
        cutoff = mw.col.sched.day_cutoff
        start = (cutoff - days * 86400) * 1000
        rows = mw.col.db.all(
            "select cast((id/1000 - ?) / 86400 as int), count() from revlog "
            "where id >= ? and type != 4 group by 1", cutoff, start)
        for offset, n in rows:
            idx = days - 1 + int(offset)      # offset is 0 for today, -1 yesterday
            if 0 <= idx < days:
                out[idx] = int(n)
    except Exception:
        pass
    return out


def today_key():
    lt = time.localtime()
    return "%04d-%02d-%02d" % (lt.tm_year, lt.tm_mon, lt.tm_mday)


def load_notes():
    try:
        with open(NOTES_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def save_note(text):
    notes = load_notes()
    key = today_key()
    if text.strip():
        notes[key] = text
    else:
        notes.pop(key, None)
    # keep it from growing forever
    for old in sorted(notes)[:-400]:
        notes.pop(old, None)
    try:
        with open(NOTES_PATH, "w", encoding="utf-8") as fh:
            json.dump(notes, fh, ensure_ascii=False, indent=1)
        return True
    except Exception:
        return False


def stats_today():
    """Everything here comes from revlog, which Anki already keeps -- no extra
    bookkeeping and nothing that can drift out of sync with the real numbers."""
    out = {"minutes": 0, "seconds": 0, "time": "0 dtk",
           "accuracy": None, "name": "", "date": ""}
    try:
        out["name"] = (mw.pm.name or "").upper()
    except Exception:
        pass
    lt = time.localtime()
    out["date"] = "%d %s" % (lt.tm_mday, BULAN[lt.tm_mon - 1])
    try:
        cutoff = mw.col.sched.day_cutoff
        start = (cutoff - 86400) * 1000
        ms = mw.col.db.scalar(
            "select sum(time) from revlog where id >= ? and type != 4", start) or 0
        secs = int(ms / 1000)
        out["seconds"] = secs
        # "0 mnt" after a short session reads as broken, so scale the unit
        if secs < 60:
            out["time"] = "%d dtk" % secs
        elif secs < 3600:
            out["time"] = "%d mnt" % (secs // 60)
        else:
            out["time"] = "%dj %dm" % (secs // 3600, (secs % 3600) // 60)
        out["minutes"] = secs // 60
        # type 1 = review, 2 = relearn. First-time learning steps are excluded:
        # pressing Again there is normal and would drag the number down.
        total = mw.col.db.scalar(
            "select count() from revlog where id >= ? and type in (1,2)", start) or 0
        again = mw.col.db.scalar(
            "select count() from revlog where id >= ? and type in (1,2) and ease = 1",
            start) or 0
        if total:
            out["accuracy"] = round((total - again) * 100 / total)
    except Exception:
        pass
    return out


def state():
    c = conf()
    target = int(c.get("daily_target") or 100)
    done = reviews_today()
    due = due_total()
    streak = streak_days()

    if due == 0 and done > 0:
        mood = "clear"
    elif done >= target:
        mood = "target"
    elif done == 0 and due > 0:
        mood = "reminder"
    elif streak == 0 and done == 0:
        mood = "broken"
    elif done >= target * 0.75:
        mood = "close"
    else:
        mood = "behind"

    return {"target": target, "done": done, "due": due,
            "streak": streak, "mood": mood}


def pick_line(mood, s):
    lines = LINES_()
    pool = lines.get(mood) or lines.get("chatter") or [""]
    try:
        return random.choice(pool).format(**s)
    except (KeyError, IndexError):
        # a typo in a custom line must not take the deck screen down
        return random.choice(pool)


def pick_pic(mood, pics):
    for want in MOODS_().get(mood, ["normal"]):
        if pics.get(want):
            return random.choice(pics[want])
    for fallback in ("normal", "indifferent"):
        if pics.get(fallback):
            return random.choice(pics[fallback])
    for names in pics.values():
        if names:
            return random.choice(names)
    return None


def build_html():
    c = conf()
    if not c.get("show_on_deck_list", True):
        return ("", "")

    s_state = state()
    s = s_state
    pics = pictures()
    first = pick_pic(s["mood"], pics)

    if not first:
        body = (
            "<div class='amd-empty'>Belum ada gambar.<br>"
            "Taruh file di folder <b>character/</b> di dalam folder addon ini, "
            "lalu buka ulang Anki.</div>"
        )
        portrait = ""
    else:
        body = ""
        base = "/_addons/%s/character/" % ADDON
        portrait = (
            "<img class='amd-img amd-base' src='{u}{f}'>"
            "<img class='amd-img amd-ghost amd-r' src='{u}{f}'>"
            "<img class='amd-img amd-ghost amd-c' src='{u}{f}'>"
            "<img class='amd-img amd-slice' src='{u}{f}'>"
        ).format(u=base, f=first)

    theme = "amd-holo" if c.get("theme") == "holo" else "amd-vhs"
    fx = "" if c.get("effects", True) else " amd-noeffects"
    width = int(c.get("panel_width") or 250)
    height = int(c.get("panel_height") or 430)
    deck_h = int(c.get("deck_max_height") or 430)
    if not c.get("deck_scroll", True):
        deck_h = 100000        # tall enough that nothing ever scrolls

    # Everything the browser side needs, handed over as a data attribute so the
    # script never has to call back into Python. Escaped, because a line with
    # an apostrophe in it would otherwise close the attribute and break the panel.
    payload = _html.escape(json.dumps({
        "pics": {m: ["/_addons/%s/character/%s" % (ADDON, n) for n in v]
                 for m, v in pics.items()},
        "moodFor": MOODS_(),
        "lines": {k: [_safe_fmt(t, s) for t in v] for k, v in LINES_().items()},
        "chatter": int(c.get("chatter_seconds") or 40),
    }), quote=True)

    css = """
/* Anki renders the deck table and the stats area as siblings inside <center>.
   Turning that into a flex row puts the companion and the decks in one block,
   which behaves far better than a floating panel: nothing overlaps and the
   page still centres itself. */
center{{display:flex !important;flex-wrap:wrap;align-items:flex-start;
  justify-content:center;gap:18px;padding:18px 14px}}
/* Other add-ons (Review Heatmap, Leaderboard...) also drop elements in here.
   As flex items they default to order 0 and would jump above the decks, so
   everything unrecognised is parked full-width at the bottom. */
center>*{{order:4;flex-basis:100%}}
center>br{{display:none}}
center>.amd-stage{{order:2;flex:0 1 auto;flex-basis:auto;position:relative;margin:0}}
.amd-deckbox{{max-height:{dh}px;box-sizing:border-box;
  overflow-y:auto;overflow-x:hidden;padding:12px 16px;position:relative}}
.amd-deckbox table{{margin:0}}
.amd-deckbox::-webkit-scrollbar{{width:10px}}
.amd-deckbox::-webkit-scrollbar-track{{background:transparent}}
#studiedToday{{order:3;flex-basis:100%;text-align:center;margin-top:4px}}
.amd-side{{position:absolute;right:calc(100% + 18px);top:0;width:{w}px;
  display:flex;flex-direction:column;gap:12px}}
.amd-right{{position:absolute;left:calc(100% + 18px);top:0;width:{rw}px;
  display:flex;flex-direction:column;gap:12px}}
.amd-card{{padding:12px 14px;font-family:system-ui,sans-serif;font-size:12.5px;
  display:flex;flex-direction:column;gap:8px}}
.amd-card .amd-head{{display:flex;justify-content:space-between;font-size:11px;
  letter-spacing:.12em;padding-bottom:7px}}
.amd-bars{{display:flex;align-items:flex-end;gap:3px;height:54px}}
.amd-bars i{{flex:1;display:block;min-height:3px}}
.amd-card textarea{{width:100%;box-sizing:border-box;resize:vertical;
  font-family:inherit;font-size:12.5px;line-height:1.5;padding:8px;
  border-radius:0;outline:none}}
#amd-panel{{position:relative;width:100%;height:{h}px;overflow:hidden;
  display:flex;flex-direction:column;justify-content:flex-end;
  cursor:pointer;font-family:system-ui,sans-serif}}
/* On a narrow window the portrait would hang off the left edge, so it drops
   back above the decks instead of disappearing. */
@media (max-width:1400px){{
  .amd-right{{position:static;margin:12px auto 0;left:auto;width:100%;max-width:420px}}
}}
@media (max-width:1000px){{
  .amd-side{{position:static;margin:0 auto 12px;right:auto;order:-1}}
  center>.amd-stage{{display:flex;flex-direction:column;align-items:center}}
}}
.amd-img{{position:absolute;left:50%;bottom:0;height:100%;width:auto;
  max-width:none !important;transform:translateX(-50%);pointer-events:none}}
.amd-scan,.amd-noise,.amd-track{{position:absolute;inset:0;pointer-events:none}}
.amd-scan{{background:repeating-linear-gradient(180deg,rgba(0,0,0,.34) 0 1px,transparent 1px 3px)}}
.amd-noise{{opacity:.15;mix-blend-mode:overlay;background-repeat:repeat;
  animation:amdCrawl .6s steps(3) infinite}}
@keyframes amdCrawl{{0%{{background-position:0 0}}33%{{background-position:-14px 9px}}
  66%{{background-position:11px -7px}}100%{{background-position:0 0}}}}
.amd-track{{height:44px;inset:auto 0 auto 0;
  background:linear-gradient(180deg,transparent,rgba(255,255,255,.10) 45%,transparent);
  animation:amdRoll 5.5s linear infinite}}
@keyframes amdRoll{{0%{{top:-50%}}100%{{top:110%}}}}
#amd-stats{{padding:12px 14px;font-family:system-ui,sans-serif;font-size:12.5px;
  display:flex;flex-direction:column;gap:5px}}
#amd-stats .amd-who{{display:flex;justify-content:space-between;
  font-size:11px;letter-spacing:.12em;margin-bottom:4px;padding-bottom:6px}}
#amd-stats .amd-line{{display:flex;justify-content:space-between;align-items:baseline}}
#amd-stats .amd-line b{{font-variant-numeric:tabular-nums;font-weight:600}}
#amd-stats .amd-meter{{height:6px;margin-top:7px;overflow:hidden}}
#amd-stats .amd-meter i{{display:block;height:100%}}
#amd-say{{position:relative;z-index:3;padding:10px 12px;font-size:13px;line-height:1.5;
  min-height:64px}}
#amd-stamp{{position:absolute;top:8px;left:10px;z-index:3;font-size:10px;letter-spacing:.1em;
  font-family:ui-monospace,monospace}}
.amd-empty{{position:relative;z-index:3;padding:14px;font-size:12px;line-height:1.6;
  color:#9c90b4}}
#amd-panel.amd-jolt .amd-img{{animation:amdJolt .34s steps(2)}}
@keyframes amdJolt{{0%{{transform:translate(calc(-50% - 8px))}}
  30%{{transform:translate(calc(-50% + 7px))}}
  60%{{transform:translate(calc(-50% - 4px))}}100%{{transform:translateX(-50%)}}}}
#amd-panel.amd-jolt .amd-noise{{opacity:.4}}

.amd-vhs{{background:#151020;border-right:2px solid #2b1f3d}}
.amd-vhs .amd-ghost{{mix-blend-mode:screen;opacity:.5}}
.amd-vhs .amd-r{{filter:sepia(1) hue-rotate(-40deg) saturate(6)}}
.amd-vhs .amd-c{{filter:sepia(1) hue-rotate(150deg) saturate(6)}}
.amd-vhs .amd-slice{{display:none}}
.amd-vhs #amd-say{{background:rgba(13,11,18,.9);border-top:2px solid #ff2d55;color:#f2ecff}}
.amd-vhs #amd-stamp{{color:#ffb200}}
.amd-card.amd-vhs{{background:#151020;border:2px solid #2b1f3d;color:#a99cc4}}
.amd-card.amd-vhs .amd-head{{color:#ffb200;border-bottom:1px solid #2b1f3d}}
.amd-card.amd-vhs .amd-bars i{{background:#3a2b52}}
.amd-card.amd-vhs .amd-bars i:last-child{{background:#ff2d55}}
.amd-card.amd-vhs textarea{{background:#0d0b12;color:#e6dcf5;border:1px solid #2b1f3d}}
.amd-card.amd-vhs textarea:focus{{border-color:#ff2d55}}
#amd-stats.amd-vhs{{background:#151020;border:2px solid #2b1f3d;color:#a99cc4}}
#amd-stats.amd-vhs .amd-who{{color:#ffb200;border-bottom:1px solid #2b1f3d}}
#amd-stats.amd-vhs .amd-line b{{color:#f2ecff}}
#amd-stats.amd-vhs .amd-meter{{background:#241a35}}
#amd-stats.amd-vhs .amd-meter i{{background:linear-gradient(90deg,#ff2d55,#ffb200)}}

.amd-holo{{background:#0f1722;border-right:1px solid #1d3448}}
.amd-holo .amd-base{{filter:grayscale(1) sepia(1) hue-rotate(155deg) saturate(3.4) brightness(1.1);
  opacity:.92}}
.amd-holo .amd-ghost{{display:none}}
.amd-holo .amd-slice{{clip-path:inset(38% 0 46% 0);
  filter:grayscale(1) sepia(1) hue-rotate(255deg) saturate(4) brightness(1.15);
  animation:amdSlice 4.2s steps(1) infinite}}
@keyframes amdSlice{{0%,72%{{transform:translateX(-50%);opacity:0}}
  74%{{transform:translate(calc(-50% + 9px));opacity:.9}}
  78%{{transform:translate(calc(-50% - 7px));opacity:.9}}
  82%,100%{{transform:translateX(-50%);opacity:0}}}}
.amd-holo #amd-say{{background:rgba(8,13,20,.88);border-top:1px solid #35d6ff;color:#d9e8f7}}
.amd-holo #amd-stamp{{color:#35d6ff}}
.amd-card.amd-holo{{background:#0f1722;border:1px solid #1d3448;color:#7f9cb5}}
.amd-card.amd-holo .amd-head{{color:#35d6ff;border-bottom:1px solid #1d3448}}
.amd-card.amd-holo .amd-bars i{{background:#22405a}}
.amd-card.amd-holo .amd-bars i:last-child{{background:#35d6ff}}
.amd-card.amd-holo textarea{{background:#080d14;color:#d9e8f7;border:1px solid #1d3448}}
.amd-card.amd-holo textarea:focus{{border-color:#35d6ff}}
#amd-stats.amd-holo{{background:#0f1722;border:1px solid #1d3448;color:#7f9cb5}}
#amd-stats.amd-holo .amd-who{{color:#35d6ff;border-bottom:1px solid #1d3448}}
#amd-stats.amd-holo .amd-line b{{color:#d9e8f7}}
#amd-stats.amd-holo .amd-meter{{background:#16283a}}
#amd-stats.amd-holo .amd-meter i{{background:linear-gradient(90deg,#35d6ff,#ff4fd8)}}

.amd-noeffects .amd-noise,.amd-noeffects .amd-track,
.amd-noeffects .amd-slice,.amd-noeffects .amd-r,.amd-noeffects .amd-c{{
  display:none !important;animation:none !important}}
@media (prefers-reduced-motion: reduce){{
  .amd-noise,.amd-track,.amd-slice,#amd-panel.amd-jolt .amd-img{{animation:none}}
}}
"""

    markup = """
<div class="amd-side">
<div id="amd-panel" class="{theme}{fx}" data-amd='{payload}'>
  <span id="amd-stamp">{stamp}</span>
  {portrait}
  <div class="amd-scan"></div><div class="amd-noise"></div><div class="amd-track"></div>
  <div id="amd-say">{line}</div>
  {body}
</div>
{stats}
</div>
{right}

<script>
(function(){{
  // Anki emits the deck table bare; a table cannot scroll on its own without
  // losing its column widths, so wrap it and scroll the wrapper instead.
  var t=document.querySelector("center > table");
  if(t&&!document.querySelector(".amd-stage")){{
    var stage=document.createElement("div");
    stage.className="amd-stage";
    var box=document.createElement("div");
    box.className="amd-deckbox";
    t.parentNode.insertBefore(stage,t);
    stage.appendChild(box);
    box.appendChild(t);
    var side=document.querySelector(".amd-side");
    if(side)stage.appendChild(side);   // portrait + stats anchor to the deck box
    var right=document.querySelector(".amd-right");
    if(right)stage.appendChild(right);
  }}

  // the note saves itself a moment after you stop typing, so there is no
  // save button to forget about
  var note=document.getElementById("amd-note");
  if(note&&!note.dataset.amdReady){{
    note.dataset.amdReady="1";
    var flag=document.getElementById("amd-saved"),wait=null;
    note.addEventListener("input",function(){{
      clearTimeout(wait);
      wait=setTimeout(function(){{
        pycmd("amd_note:"+note.value);
        if(flag){{flag.textContent="tersimpan";
          setTimeout(function(){{flag.textContent=""}},1600);}}
      }},700);
    }});
  }}

  var panel=document.getElementById("amd-panel");
  if(!panel||panel.dataset.amdReady)return;
  panel.dataset.amdReady="1";
  var D={{}};
  try{{D=JSON.parse(panel.dataset.amd)}}catch(e){{return}}
  var say=document.getElementById("amd-say");
  var imgs=panel.querySelectorAll(".amd-img");
  var timer=null,chat=null;

  function pick(a){{return a[(Math.random()*a.length)|0]}}
  function picFor(mood){{
    var order=(D.moodFor&&D.moodFor[mood])||["normal"];
    for(var i=0;i<order.length;i++){{
      var list=D.pics[order[i]];
      if(list&&list.length)return pick(list);
    }}
    var keys=Object.keys(D.pics||{{}});
    return keys.length?pick(D.pics[keys[0]]):null;
  }}
  function show(mood){{
    var src=picFor(mood);
    if(src)for(var i=0;i<imgs.length;i++)imgs[i].src=src;
    var pool=(D.lines&&D.lines[mood])||[];
    if(pool.length)say.textContent=pick(pool);
    panel.classList.remove("amd-jolt");void panel.offsetWidth;
    panel.classList.add("amd-jolt");
  }}
  function settle(ms){{
    clearTimeout(timer);
    timer=setTimeout(function(){{show("chatter")}},ms||4500);
  }}
  panel.addEventListener("click",function(){{
    show("poke");settle(4000);restart();
  }});
  function restart(){{
    clearInterval(chat);
    chat=setInterval(function(){{show("chatter")}},(D.chatter||40)*1000);
  }}
  restart();
}})();
</script>
"""
    st = stats_today()
    if c.get("show_stats", True):
        back = backlog()
        backlog_html = ""
        if back > s_state["due"]:
            backlog_html = ('<div class="amd-line"><span>Tunggakan</span>'
                            '<b>%d</b></div>' % back)
        acc = "%d%%" % st["accuracy"] if st["accuracy"] is not None else "-"
        stats_html = (
            '<div id="amd-stats" class="{theme}">'
            '<div class="amd-who"><span>{name}</span><span>{date}</span></div>'
            '<div class="amd-line"><span>Hari ini</span><b>{done} / {target}</b></div>'
            '<div class="amd-line"><span>Waktu</span><b>{mins}</b></div>'
            '<div class="amd-line"><span>Streak</span><b>{streak} hari</b></div>'
            '<div class="amd-line"><span>Sisa hari ini</span><b>{due}</b></div>'
            '{backlog}'
            '<div class="amd-line"><span>Akurasi</span><b>{acc}</b></div>'
            '<div class="amd-meter"><i style="width:{pct}%"></i></div>'
            '</div>'
        ).format(theme=theme, name=_html.escape(st["name"] or "ANKI"),
                 date=st["date"], done=s_state["done"], target=s_state["target"],
                 mins=st["time"], streak=s_state["streak"],
                 due=s_state["due"], acc=acc, backlog=backlog_html,
                 pct=min(100, int(s_state["done"] * 100 / max(1, s_state["target"]))))
    else:
        stats_html = ""

    right = ""
    if c.get("show_history", True) or c.get("show_note", True):
        blocks = []
        if c.get("show_history", True):
            days = max(3, min(int(c.get("history_days") or 14), 60))
            hist = history(days)
            top = max(hist) or 1
            bars = "".join(
                '<i style="height:%d%%" title="%d"></i>' % (
                    max(4, int(v * 100 / top)), v) for v in hist)
            blocks.append(
                '<div class="amd-card {theme}"><div class="amd-head">'
                '<span>{d} HARI</span><span>{tot}</span></div>'
                '<div class="amd-bars">{bars}</div></div>'.format(
                    theme=theme, d=days, tot=sum(hist), bars=bars))
        if c.get("show_note", True):
            note = load_notes().get(today_key(), "")
            blocks.append(
                '<div class="amd-card {theme}"><div class="amd-head">'
                '<span>CATATAN</span><span id="amd-saved"></span></div>'
                '<textarea id="amd-note" rows="6" placeholder="Apa yang kamu '
                'pelajari hari ini?">{n}</textarea></div>'.format(
                    theme=theme, n=_html.escape(note)))
        right = '<div class="amd-right">%s</div>' % "".join(blocks)

    sheet = css.format(w=width, h=height, dh=deck_h, rw=int(c.get("right_width") or 230))
    if c.get("theme_deck_list", True):
        key = "holo" if c.get("theme") == "holo" else "vhs"
        sheet += DECK_CSS[key].replace("{{", "{").replace("}}", "}")
    return (sheet,
            markup.format(theme=theme, fx=fx, payload=payload, stats=stats_html,
                          right=right,
                          portrait=portrait, body=body,
                          line=_html.escape(pick_line(s["mood"], s)),
                          stamp="&#9673; %d/%d" % (s["done"], s["target"])))


_pending_css = ""


def on_deck_browser(deck_browser, content: DeckBrowserContent) -> None:
    """Build the panel. The stylesheet is stashed for the head injector below."""
    global _pending_css
    try:
        css, markup = build_html()
        _pending_css = css
        content.stats += markup
    except Exception as exc:
        # A broken companion must never stop the deck list from rendering.
        _pending_css = ""
        content.stats += (
            "<div style='color:#c66;font-size:12px'>Amadeus Deck: %s</div>"
            % _html.escape(str(exc)))


def on_webview_content(web_content, context) -> None:
    """Anki puts web_content.head after its own stylesheets, so rules placed
    here win. A <style> tag inside the body loses to Anki's theme."""
    import aqt.deckbrowser
    import aqt.toolbar

    c = conf()

    # the deck page itself
    if isinstance(context, aqt.deckbrowser.DeckBrowser):
        if _pending_css:
            web_content.head += "<style>%s</style>" % _pending_css
        return

    if not c.get("theme_bars", True):
        return

    # The button bar and the top toolbar are separate webviews, which is why
    # they kept their default look while the deck page was themed.
    key = "holo" if c.get("theme") == "holo" else "vhs"
    if isinstance(context, aqt.deckbrowser.DeckBrowserBottomBar):
        if c.get("hide_bottom_bar", False):
            web_content.head += "<style>body{display:none !important}</style>"
        else:
            web_content.head += "<style>%s</style>" % BAR_CSS[key]
    elif isinstance(context, (aqt.toolbar.TopToolbar, aqt.toolbar.BottomToolbar)):
        web_content.head += "<style>%s</style>" % BAR_CSS[key]


gui_hooks.deck_browser_will_render_content.append(on_deck_browser)
gui_hooks.webview_will_set_content.append(on_webview_content)

def on_js_message(handled, message, context):
    """The note box talks back through pycmd; everything else is left alone."""
    if not message.startswith("amd_note:"):
        return handled
    save_note(message[len("amd_note:"):])
    return (True, None)


gui_hooks.webview_did_receive_js_message.append(on_js_message)


# --- the reviewer half lives in its own file; it shares nothing with the deck
# screen except the character folder -------------------------------------------
try:
    from . import reviewer as _reviewer

    _reviewer.register()
except Exception as _exc:  # a broken reviewer must not take the deck list down
    print("Amadeus Deck: reviewer tidak aktif (%s)" % _exc)
