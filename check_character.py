#!/usr/bin/env python3
"""
Check a character folder against what Amadeus Deck actually asks for.

Run it after dropping in a new set (your OC, another character, anything):

    python3 check_character.py                 # checks ./character
    python3 check_character.py /path/to/folder

It reports which expressions are covered, which states would silently fall back
to something else, and any file that the add-on will ignore because its name
does not end in a mood it recognises.

Anki never imports this file -- only __init__.py is loaded.
"""

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

MOODS = [
    "normal", "happy", "winking", "sided_pleasant", "sided_thinking",
    "disappointed", "sad", "annoyed", "pissed", "angry", "blush",
    "sided_blush", "eyes_closed", "sided_worried", "sided_surprised",
    "indifferent", "side",
]

EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif")


def load_state_map():
    """Which expressions each state prefers, straight from the live config so
    this never drifts from what the add-on really does."""
    try:
        with open(os.path.join(HERE, "config.json"), encoding="utf-8") as fh:
            cfg = json.load(fh)
        out = {}
        for key in ("moods", "reviewer_moods"):
            for state, order in (cfg.get(key) or {}).items():
                out.setdefault(("review " if key.startswith("rev") else "deck ") + state, order)
        return out
    except Exception as exc:
        print("  (tidak bisa membaca config.json: %s)" % exc)
        return {}


def scan(folder):
    found, ignored = {}, []
    for name in sorted(os.listdir(folder)):
        if not name.lower().endswith(EXT):
            continue
        stem = re.sub(r"\d+$", "", os.path.splitext(name)[0])
        for mood in sorted(MOODS, key=len, reverse=True):
            if stem.endswith(mood):
                found.setdefault(mood, []).append(name)
                break
        else:
            ignored.append(name)
    return found, ignored


def sizes(folder, names):
    out = {}
    for n in names:
        try:
            r = subprocess.run(["identify", "-format", "%wx%h|%A", os.path.join(folder, n)],
                               capture_output=True, text=True, timeout=10)
            out[n] = r.stdout.strip()
        except Exception:
            out[n] = "?"
    return out


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "character")
    if not os.path.isdir(folder):
        print("Folder tidak ada:", folder)
        return 1

    print("Folder :", folder)
    found, ignored = scan(folder)
    total = sum(len(v) for v in found.values())
    print("Gambar terpakai : %d dalam %d ekspresi" % (total, len(found)))
    print()

    print("EKSPRESI")
    for mood in MOODS:
        n = len(found.get(mood, []))
        mark = "  " if n else "  <- kosong"
        print("  %-18s %d%s" % (mood, n, mark))

    if ignored:
        print()
        print("DIABAIKAN (nama tidak diakhiri ekspresi yang dikenal)")
        for n in ignored[:12]:
            print("  ", n)
        if len(ignored) > 12:
            print("   ... dan %d lagi" % (len(ignored) - 12))
        print("  Ganti namanya jadi <apa saja>_<ekspresi><angka>.png")

    print()
    print("STATE -> EKSPRESI YANG DIPAKAI")
    fallbacks = 0
    for state, order in sorted(load_state_map().items()):
        hit = next((m for m in order if found.get(m)), None)
        if hit == (order[0] if order else None):
            print("  %-22s %s" % (state, hit))
        elif hit:
            print("  %-22s %s   (mundur dari %s)" % (state, hit, order[0]))
            fallbacks += 1
        else:
            spare = next((m for m in ("normal", "indifferent") if found.get(m)), None)
            print("  %-22s TIDAK ADA -> %s" % (state, spare or "tidak ada sama sekali"))
            fallbacks += 1

    print()
    if total:
        info = sizes(folder, sorted(sum(found.values(), []))[:60])
        dims = {}
        no_alpha = []
        for n, v in info.items():
            if "|" not in v:
                continue
            d, a = v.split("|")
            dims[d] = dims.get(d, 0) + 1
            if a.lower() != "true":
                no_alpha.append(n)
        print("UKURAN")
        for d, n in sorted(dims.items(), key=lambda x: -x[1]):
            print("  %-12s %d file" % (d, n))
        if len(dims) > 1:
            print("  Ukuran campur bikin potretnya melompat tiap ganti ekspresi.")
        if no_alpha:
            print("  Tanpa latar transparan: %d file (%s...)" % (len(no_alpha), no_alpha[0]))
        else:
            print("  Semua punya latar transparan.")

    print()
    if fallbacks:
        print("Kesimpulan: jalan, tapi %d state memakai ekspresi pengganti." % fallbacks)
    else:
        print("Kesimpulan: lengkap. Semua state punya ekspresinya sendiri.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
