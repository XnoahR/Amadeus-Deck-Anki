# Amadeus Deck

[Bahasa Indonesia](README-id.md)

An Anki add-on that puts a character on your deck screen and beside your reviews.
She reacts to how the session is going: pleased when you answer well, visibly
irritated when you press Again five times in a row, disappointed when a streak
breaks.

Inspired by Project Amadeus from Steins;Gate 0.

![Amadeus Deck on the deck screen](docs/screenshot.png)

*The character shown is not included — see [Bring your own character](#bring-your-own-character).*

**Your note types are never touched.** No template is edited, nothing is added to
your cards, and the reviewer portrait lives in a Shadow DOM so your card CSS and
the add-on cannot reach each other. Remove the add-on and your collection is
exactly as it was.

---

## Bring your own character

The add-on ships with **no images**. Drop yours into the `character/` folder
inside the add-on directory:

```
<anki data>/addons21/amadeus_deck/character/
```

Name each file so it **ends with a mood and a number**:

```
myoc_happy1.png   myoc_annoyed2.png   myoc_sided_thinking1.png
```

The prefix is free — only the ending matters. Several files per mood is better;
one is picked at random so the same face does not repeat.

**Moods it looks for**

Front-facing: `normal` `happy` `winking` `blush` `disappointed` `sad` `annoyed`
`pissed` `angry` `eyes_closed` `indifferent`

Turned: `side` `sided_pleasant` `sided_thinking` `sided_blush` `sided_worried`
`sided_surprised`

Only `normal` is really required — everything else falls back to it. Check what
you have with:

```
python3 check_character.py
```

It reports which moods are covered, which states would fall back, and whether
your files are consistent in size and transparency.

**Suggested format:** PNG with a transparent background, portrait crop around
454×810, head near the top edge. Mixed sizes make the portrait jump between
expressions.

> Character art is usually somebody else's copyright. That is why none is
> bundled here: what you keep on your own machine is your business, but a
> repository shipping someone's character is a different matter. It also means
> everyone gets to use the character they actually want.

---

## What it adds

**On the deck screen** — a portrait beside your decks, a summary card
(reviews today, time, streak, backlog, accuracy), a bar chart of recent days,
and a daily note that saves itself as you type. The deck list is themed to match
and can scroll instead of growing down the page.

**During review** — the portrait sits in a corner and changes expression as you
answer. Press Again three times in a row and she gets annoyed; five and she tells
you to take a break.

**Eight themes** — `vhs`, `holo`, `amber`, `divergence`, `paper` (the only light
one), `slate`, `sakura`, `mint`. Scanlines and static can be turned off. The
settings dialog follows the theme too.

---

**Lines type themselves out** a character at a time, with an 8-bit talking
blip per syllable -- synthesised, so there is no audio file to ship. Click
mid-sentence to finish the line. Turn either off with `typewriter` and
`dialog_sound` in the config.

**Expressions can be drawn rather than swapped.** With `frame_scan` on, the frame
empties to bare scan lines for a beat and the new expression is rebuilt downwards
behind a sweeping head -- four visible bands by default, because a smooth reveal
reads as a fade while a coarse one reads as a machine drawing lines. `tracking`
adds the other half: every so often one horizontal band slips sideways and
brightens, the way a tape does when the head is off track.

Neither touches the mouth or the blink. Those change picture every 90-110ms,
faster than any sweep, so only a change of expression sweeps -- and only when the
picture actually differs.

Everything described from here down is **off by default**. A fresh install
behaves exactly as it did before these were added; you turn on what you want.

---

## Optional: her own voice, and a Live2D model

Two additions that need files **you** supply, and that stay switched off until
you turn them on. With nothing in the folders, turning them on changes nothing:
the blips and the pictures keep their job.

### Recorded lines

Drop audio into `user_files/voice/` and she speaks instead of beeping.

Two kinds live there. A **line clip** is named after the line it belongs to --
the first ten hex characters of the SHA-1 of the exact text in `lines`. Edit that
line in the config and the link breaks by itself: the result is silence for that
line, never the wrong sentence in her voice. A **reaction clip** is listed in
`react.json` under a mood, because a reaction answers *how she felt*, not *what
she said* -- the same "one more time" fits every wrong answer.

```
user_files/voice/
  b44dd8123f.ogg      one line, found by its text
  react_9f2c1a04bb.ogg
  react.json          {"annoyed": [{"file": "react_9f2c1a04bb.ogg"}], ...}
```

`ogg`, `mp3`, `wav` and `m4a` all work. When a clip plays, the 8-bit blips step
aside for that line -- turn that off with `voice_clips_hush` if you want both.

The reviewer names its states after what happened to the card (`good`, `wrong`)
while the chat panel names its faces after how she feels (`happy`, `annoyed`).
The add-on translates between them, so an answered card reaches whichever surface
is showing her with a face and a clip that exist.

### A Live2D model in the chat panel

Put a Cubism model and its runtime in `user_files/live2d/`:

```
user_files/live2d/
  lib/live2d.min.js  lib/pixi.min.js  lib/cubism2.min.js
  something.model.json + whatever it references
```

Nothing here ships. The Cubism runtime belongs to Live2D Inc. and a model belongs
to whoever drew it, exactly like the character art.

Expressions are built from parameters, so they are not limited to pictures you
have: eye openness, gaze, brow height and mouth. Her mouth follows the **sound**
while a clip is playing -- read from the audio itself, not counted off the
letters -- and follows the typing the rest of the time. A short head movement
plays with each mood, added on top of the model's own idle motion rather than
replacing it, and the expression relaxes back to neutral after a few seconds.

The canvas is only shown once a frame has actually been drawn. WebGL off, a
runtime file missing, a model that will not parse -- every one of those ends with
the PNG face still on screen.

## Configuration

**Tools → Amadeus Deck → Pengaturan** is a form, grouped into tabs and sections,
and themed like the rest of the add-on. Everything you are likely to change is
there, including the AI provider list with a *test connection* button that sends
one small request and shows the answer verbatim.

The form is a page rather than a stack of widgets, for a specific reason: as soon
as a Qt stylesheet touches `QCheckBox::indicator`, Qt drops the platform's own
painter and the tick vanishes unless every state is drawn by hand. Sliding
switches have no such problem. If the page cannot be built for any reason the old
widget dialog opens instead -- settings must stay reachable whatever else broke.

**Tools → Add-ons → Amadeus Deck → Config** is still Anki's raw JSON editor, and
still where the whole dialogue set lives, so you can rewrite every line in your
character's voice without touching code:

```json
"lines": {
  "behind": ["Sisa {due}. Baru {done} dari {target}."],
  "target": ["Target {target} tercapai. ...Kerja bagus."]
}
```

Available placeholders: `{due}` `{done}` `{target}` `{streak}`.

Override one state and the rest keep their defaults; delete a state and its
default comes back. A broken placeholder prints literally rather than breaking
the screen.

Notable options: `theme`, `daily_target`, `effects`, `panel_width`,
`panel_height`, `deck_scroll`, `deck_max_height`, `show_stats`, `show_history`,
`show_note`, `show_in_reviewer`, `reviewer_corner`, `reviewer_size`,
`reviewer_always_visible`, `frame_scan`, `tracking`, `voice_clips`, `live2d`.
Full descriptions are in the settings form.


---

## Install

**The easy way.** Download
[`AmadeusDeck.ankiaddon`](https://github.com/XnoahR/Amadeus-Deck-Anki/releases/latest/download/AmadeusDeck.ankiaddon)
and double-click it, or in Anki: **Tools → Add-ons → Install from file**.

Then add your images: **Tools → Add-ons → Amadeus Deck → View Files**, drop them
in `character/`, and restart Anki.

**From source.** Copy the folder into your Anki add-ons directory instead:

```
~/.local/share/Anki2/addons21/amadeus_deck              # Linux
~/.var/app/net.ankiweb.Anki/data/Anki2/addons21/...     # Linux, Flatpak
%APPDATA%\Anki2\addons21\amadeus_deck                   # Windows
~/Library/Application Support/Anki2/addons21/...        # macOS
```

Then put your images in `character/` and restart again.

Built against Anki 25.09. Desktop only — the deck screen and reviewer overlay are
injected into Anki's own web views, which AnkiDroid and AnkiMobile do not have.
Your cards sync normally; they simply carry none of this with them.

---

## Known limits

- **Anki updates can break it.** The deck screen is styled by redefining Anki's
  own CSS variables and by wrapping its deck table. Both are internal details
  that upstream may change without warning.
- **Statistics come from `revlog`**, the same table Anki uses, so the numbers
  match Anki's own — including the daily limits. "Backlog" is shown separately
  because the deck list only ever shows the capped number.
- **Effects animate continuously.** On a laptop that costs a little battery.
  `effects: false` turns them off, and `prefers-reduced-motion` is respected
  automatically.
- **Live2D needs WebGL in Anki's webview.** It is there on most machines, but a
  software-rendering fallback can leave it out. When that happens the canvas is
  never shown and the PNG face stays -- nothing to configure, nothing broken.
- **Audio will not start until the page is clicked once.** Browsers refuse to
  begin playback without a gesture, so the first line after opening a panel can
  be silent.
- **Desktop only.** AnkiMobile and AnkiDroid do not run Python add-ons, so none
  of this appears there. Your collection syncs normally.

## Licence

MIT for the code. Anything you add carries its own licence: character art, audio
recordings, a Live2D model, and the Cubism runtime a model needs. None of it
ships with the add-on, and the folders it looks in start empty.
