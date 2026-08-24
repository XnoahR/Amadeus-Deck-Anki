# SPDX-License-Identifier: MIT
"""Every colour in the add-on, in one table.

The look used to be a boolean -- vhs or holo -- spelled out separately in the
deck stylesheet, the bottom bars, the reviewer overlay and the chat panel. Four
places to keep in step, and a fifth theme was not a config value but an
afternoon of copying hex codes around.

So: one record per theme, and each surface builds its own CSS from it. Adding a
theme is now a dozen values in this file and nothing else.

`fx` is the only field that is not a colour. It picks which glitch a theme
wears -- an RGB split, the way a worn tape tears, or a single sliced band, the
way a projection stutters -- because that reads as part of the identity rather
than as a setting.
"""

from typing import Any

THEMES: dict[str, dict[str, Any]] = {
    "vhs": {
        "label": "VHS retro", "light": False, "fx": "split",
        "ground": "#0d0b12", "card": "#151020", "line": "#2b1f3d",
        "border": "#3a2b52", "edge": "#ff2d55",
        "ink": "#f2ecff", "dim": "#9a8fb5",
        "fg": "#cdc2e0", "fg_subtle": "#7d7194", "fg_faint": "#4b4260",
        "deck_link": "#e6dcf5",
        "new": "#00e5ff", "learn": "#ffb200", "review": "#ff6ea1",
        "gears": "invert(72%) sepia(20%) hue-rotate(215deg)",
    },
    "holo": {
        "label": "Holo biru", "light": False, "fx": "slice",
        "ground": "#080d14", "card": "#0f1722", "line": "#1d3448",
        "border": "#22405a", "edge": "#35d6ff",
        "ink": "#d9e8f7", "dim": "#7e94aa",
        "fg": "#9db6cc", "fg_subtle": "#5c7d99", "fg_faint": "#33495c",
        "deck_link": "#d9e8f7",
        "new": "#35d6ff", "learn": "#ff4fd8", "review": "#7ce0b0",
        "gears": "invert(64%) sepia(30%) hue-rotate(160deg)",
    },
    "amber": {
        "label": "Amber CRT", "light": False, "fx": "split",
        "ground": "#0f0b06", "card": "#1a1209", "line": "#3a2a12",
        "border": "#513a19", "edge": "#ffb000",
        "ink": "#ffd9a0", "dim": "#a8845a",
        "fg": "#e8bf83", "fg_subtle": "#9c7a4e", "fg_faint": "#5e4a30",
        "deck_link": "#ffd9a0",
        "new": "#ffb000", "learn": "#ff7a1a", "review": "#c8d44a",
        "gears": "invert(70%) sepia(60%) hue-rotate(1deg) saturate(220%)",
    },
    "divergence": {
        "label": "Divergence", "light": False, "fx": "slice",
        "ground": "#0c0c0d", "card": "#151517", "line": "#2c2c30",
        "border": "#3d3d43", "edge": "#ff7518",
        "ink": "#ece8e3", "dim": "#8e8a86",
        "fg": "#c9c5c0", "fg_subtle": "#807c78", "fg_faint": "#4f4c49",
        "deck_link": "#ece8e3",
        "new": "#ff7518", "learn": "#ffc46b", "review": "#8fb9c9",
        "gears": "invert(62%) sepia(40%) hue-rotate(340deg) saturate(180%)",
    },
    "paper": {
        "label": "Kertas (terang)", "light": True, "fx": "slice",
        "ground": "#f4f1ea", "card": "#ffffff", "line": "#ddd6c8",
        "border": "#c6bda9", "edge": "#b5451f",
        "ink": "#2b2724", "dim": "#7a736a",
        "fg": "#3b3630", "fg_subtle": "#7a736a", "fg_faint": "#a9a196",
        "deck_link": "#2b2724",
        "new": "#1c6b8c", "learn": "#b5451f", "review": "#3f7a4a",
        "gears": "invert(35%) sepia(20%) saturate(120%)",
    },
    "slate": {
        "label": "Slate", "light": False, "fx": "slice",
        "ground": "#14171a", "card": "#1b1f24", "line": "#2c333b",
        "border": "#3c4550", "edge": "#7aa2f7",
        "ink": "#dfe4ec", "dim": "#8b95a3",
        "fg": "#c3cad4", "fg_subtle": "#7d8894", "fg_faint": "#4e5761",
        "deck_link": "#dfe4ec",
        "new": "#7aa2f7", "learn": "#e0af68", "review": "#9ece6a",
        "gears": "invert(66%) sepia(12%) hue-rotate(185deg)",
    },
    "sakura": {
        "label": "Sakura", "light": False, "fx": "split",
        "ground": "#16101a", "card": "#1f1724", "line": "#3a2a42",
        "border": "#4d3a58", "edge": "#ff8fb1",
        "ink": "#f5e9f0", "dim": "#a892b0",
        "fg": "#d9c6df", "fg_subtle": "#96809f", "fg_faint": "#5d4d67",
        "deck_link": "#f5e9f0",
        "new": "#8fd8ff", "learn": "#ffc98f", "review": "#ff8fb1",
        "gears": "invert(74%) sepia(18%) hue-rotate(280deg)",
    },
    "mint": {
        "label": "Mint", "light": False, "fx": "slice",
        "ground": "#0a1210", "card": "#101a17", "line": "#1f3a32",
        "border": "#2c5147", "edge": "#4de0a8",
        "ink": "#d8f0e6", "dim": "#7ba896",
        "fg": "#b6d9c9", "fg_subtle": "#6f9686", "fg_faint": "#425d53",
        "deck_link": "#d8f0e6",
        "new": "#4de0a8", "learn": "#ffd166", "review": "#7ec8ff",
        "gears": "invert(70%) sepia(30%) hue-rotate(110deg)",
    },
}

DEFAULT = "vhs"


def name_of(cfg) -> str:
    """Whatever is in the config, narrowed to a theme that exists."""
    want = str((cfg or {}).get("theme") or "").strip().lower()
    return want if want in THEMES else DEFAULT


def palette(name: str) -> dict[str, Any]:
    return THEMES.get(name, THEMES[DEFAULT])


def rgba(hex_colour: str, alpha: float) -> str:
    """Accent colours are given once, as hex; the translucent tints are derived
    so a theme can never have a highlight that does not match its own accent."""
    value = hex_colour.lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    try:
        r, g, b = (int(value[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        r, g, b = 255, 255, 255
    return "rgba(%d,%d,%d,%s)" % (r, g, b, alpha)


def deck_css(name: str) -> str:
    """Anki drives its whole look from custom properties, so redefining those is
    cleaner and more complete than overriding rule by rule. This is what finally
    kills the default rounded panel behind the deck table."""
    p = palette(name)
    return """
:root,:root.night-mode{{
  --canvas:{ground};
  --canvas-glass:transparent;
  --canvas-elevated:{card};
  --canvas-inset:{ground};
  --border:{border};
  --border-subtle:{line};
  --border-strong:{edge};
  --fg:{fg};
  --fg-subtle:{fg_subtle};
  --fg-faint:{fg_faint};
  --fg-link:{edge};
  --state-new:{new};
  --state-learn:{learn};
  --state-review:{review};
  --border-radius-medium:0;
  --border-radius:0;
}}
/* the table's own card would sit inside our box and read as a double frame */
.fancy table,table{{background:transparent !important;border:0 !important;
  box-shadow:none !important;border-radius:0 !important;padding:0 !important}}
tr.current td,tr:hover:not(.top-level-drag-row) td{{background:{tint} !important}}
tr.current td:first-child{{box-shadow:inset 3px 0 0 {edge}}}
tr.current a.deck{{color:{strong} !important}}
a.deck{{color:{deck_link}}}
.amd-deckbox{{background:{card};border:2px solid {line};
  box-shadow:inset 0 0 50px {glow}}}
.amd-deckbox::-webkit-scrollbar-thumb{{background:{border} !important;border-radius:0 !important}}
.amd-deckbox::-webkit-scrollbar-thumb:hover{{background:{edge} !important}}
img.gears{{filter:{gears}}}
""".format(tint=rgba(p["edge"], .14), glow=rgba(p["edge"], .06),
           strong="#111" if p["light"] else "#fff", **p)


def bar_css(name: str) -> str:
    p = palette(name)
    return """
body{{background:{ground} !important;border-top:2px solid {line} !important}}
button{{background:{card} !important;color:{fg} !important;
  border:1px solid {line} !important;border-radius:0 !important;
  padding:6px 14px !important}}
button:hover{{background:{hover} !important;color:{strong} !important;
  border-color:{edge} !important}}
""".format(hover=rgba(p["edge"], .16), strong="#111" if p["light"] else "#fff", **p)


def choices() -> list:
    """(value, label) for the settings form, in table order."""
    return [(key, spec["label"]) for key, spec in THEMES.items()]


# One class for every theme, rather than .amd-vhs / .amd-holo / .amd-amber and
# so on. Only the active theme's rules are ever emitted, so the selector never
# needed to name which theme it was.
CLASS = "amd-t"


def panel_css(name: str) -> str:
    """The companion panel, its stats card and the daily note.

    The glitch differs by theme rather than by setting: `split` tears the
    portrait into red and cyan ghosts the way a worn tape does, `slice` stutters
    one band sideways the way a projection does.
    """
    p = palette(name)
    thick = "1px" if p["light"] else "2px"

    if p["fx"] == "split":
        glitch = """
.{k} .amd-ghost{{{{mix-blend-mode:screen;opacity:.5}}}}
.{k} .amd-r{{{{filter:sepia(1) hue-rotate(-40deg) saturate(6)}}}}
.{k} .amd-c{{{{filter:sepia(1) hue-rotate(150deg) saturate(6)}}}}
.{k} .amd-slice{{{{display:none}}}}
""".format(k=CLASS)
    else:
        glitch = """
.{k} .amd-base{{{{filter:grayscale(1) sepia(1) hue-rotate({hue}deg) saturate(3.4)
  brightness(1.1);opacity:.92}}}}
.{k} .amd-ghost{{{{display:none}}}}
.{k} .amd-slice{{{{opacity:0;clip-path:inset(38% 0 46% 0);
  filter:grayscale(1) sepia(1) hue-rotate({hue2}deg) saturate(4) brightness(1.15);
  animation:amdSlice 4.2s steps(1) infinite}}}}
@keyframes amdSlice{{{{0%,72%{{{{transform:translateX(-50%);opacity:0}}}}
  74%{{{{transform:translate(calc(-50% + 9px));opacity:.9}}}}
  78%{{{{transform:translate(calc(-50% - 7px));opacity:.9}}}}
  82%,100%{{{{transform:translateX(-50%);opacity:0}}}}}}}}
""".format(k=CLASS, hue=rotations(name)[0], hue2=rotations(name)[1])

    return (glitch + """
.{k}{{{{background:{{card}};border-right:{t} solid {{line}}}}}}
.{k} #amd-say{{{{background:{{saybg}};border-top:{t} solid {{edge}};color:{{ink}}}}}}
.{k} #amd-stamp{{{{color:{{learn}}}}}}
.amd-card.{k}{{{{background:{{card}};border:{t} solid {{line}};color:{{fg}}}}}}
.amd-card.{k} .amd-head{{{{color:{{learn}};border-bottom:1px solid {{line}}}}}}
.amd-card.{k} .amd-bars i{{{{background:{{border}}}}}}
.amd-card.{k} .amd-bars i:last-child{{{{background:{{edge}}}}}}
.amd-card.{k} textarea{{{{background:{{ground}};color:{{deck_link}};
  border:1px solid {{line}}}}}}
.amd-card.{k} textarea:focus{{{{border-color:{{edge}}}}}}
#amd-stats.{k}{{{{background:{{card}};border:{t} solid {{line}};color:{{fg}}}}}}
#amd-stats.{k} .amd-who{{{{color:{{learn}};border-bottom:1px solid {{line}}}}}}
#amd-stats.{k} .amd-line b{{{{color:{{ink}}}}}}
#amd-stats.{k} .amd-meter{{{{background:{{meter}}}}}}
#amd-stats.{k} .amd-meter i{{{{background:linear-gradient(90deg,{{edge}},{{learn}})}}}}
""".format(k=CLASS, t=thick)).format(
        saybg=rgba(p["ground"], .9), meter=rgba(p["edge"], .16), **p)


# sepia(1) lands the image around this hue before hue-rotate is applied, so a
# rotation has to be measured from here rather than from zero. Getting this
# wrong tints every slice theme 35 degrees off its own accent.
SEPIA_BASE = 35


def rotations(name: str) -> tuple[int, int]:
    """How far to turn a sepia-converted portrait to reach the theme's accent,
    and the offset used for the sliced band."""
    base = (_hue(palette(name)["edge"]) - SEPIA_BASE) % 360
    return base, (base + 110) % 360


def _hue(hex_colour: str) -> int:
    """Roughly where the accent sits on the colour wheel, so a themed filter can
    aim at it instead of at a number copied from another theme."""
    import colorsys

    value = hex_colour.lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    try:
        r, g, b = (int(value[i:i + 2], 16) / 255 for i in (0, 2, 4))
    except ValueError:
        return 0
    return int(colorsys.rgb_to_hls(r, g, b)[0] * 360)
