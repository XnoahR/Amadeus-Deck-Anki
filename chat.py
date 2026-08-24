# SPDX-License-Identifier: AGPL-3.0-or-later
"""Talking to her.

The panel is a web view rather than plain Qt widgets, which is the whole reason
this was cheap to build: the portrait, the VHS treatment, the typewriter and the
8-bit voice already exist as HTML in this add-on. A Qt transcript would have
meant writing all four again, worse.

The model streams; the typewriter reveals at its own pace. Those are separate
speeds on purpose -- a reply that arrives in three bursts still reads as someone
speaking evenly.
"""

from __future__ import annotations

import json
import threading
from typing import Any

from aqt import gui_hooks, mw
from aqt.qt import (
    QComboBox, QDockWidget, QKeySequence, QHBoxLayout, QPlainTextEdit,
    QPushButton, QShortcut, QSize, Qt, QVBoxLayout, QWidget,
)
from aqt.utils import showWarning, tooltip
from aqt.webview import AnkiWebView

from . import cardctx, chatconf, providers, voice

DOCK_NAME = "amadeusChatDock"
TITLE = "Amadeus"


class MoodHead:
    """She is asked to open with `[mood] `. Hold the first few characters back
    until the tag can be recognised, so it never flickers on screen before it
    gets stripped. If it never comes, everything held back is released."""

    LIMIT = 40

    def __init__(self, allowed):
        self.allowed = set(allowed)
        self.buf = ""
        self.done = False

    def feed(self, delta):
        """-> (mood or None, text to display)"""
        if self.done:
            return None, delta
        self.buf += delta
        head = self.buf.lstrip()
        if not head:
            return None, ""
        if not head.startswith("["):
            self.done = True
            out, self.buf = self.buf, ""
            return None, out
        close = head.find("]")
        if close < 0:
            if len(head) > self.LIMIT:      # not a tag after all
                self.done = True
                out, self.buf = self.buf, ""
                return None, out
            return None, ""                 # still waiting
        name = head[1:close].strip().lower()
        rest = head[close + 1:].lstrip()
        self.done = True
        self.buf = ""
        return (name if name in self.allowed else None), rest

    def flush(self):
        out, self.buf, self.done = self.buf, "", True
        return out


def study_summary():
    """The figures she is allowed to know. Assembled here rather than typed by
    anyone -- being able to mention the backlog unprompted is the difference
    between a companion and a chat box."""
    from . import backlog, reviews_today, stats_today, streak_days, due_total

    try:
        st = stats_today()
        lines = [
            "- Review hari ini: %d" % reviews_today(),
            "- Waktu belajar hari ini: %s" % st["time"],
            "- Streak: %d hari" % streak_days(),
            "- Sisa jatuh tempo hari ini: %d" % due_total(),
        ]
        back = backlog()
        if back > due_total():
            lines.append("- Tunggakan menumpuk: %d kartu" % back)
        if st.get("accuracy") is not None:
            lines.append("- Akurasi hari ini: %d%%" % st["accuracy"])
        return "\n".join(lines)
    except Exception:
        return ""


def _page(cfg, pics, theme):
    vhs = theme != "holo"
    ink, edge = ("#f2ecff", "#ff2d55") if vhs else ("#d9e8f7", "#35d6ff")
    ground = "#0d0b12" if vhs else "#080d14"
    face = json.dumps({m: ["/_addons/%s/character/%s" % (chatconf.PACKAGE, n)
                           for n in v] for m, v in pics.items()})
    # The reviewer speaks a different mood vocabulary (good/wrong/pissed) from
    # the chat (happy/sad/thinking). Since one panel now shows both, it has to
    # know both names -- otherwise every reaction to a card falls back to a
    # blank face. Chat names win where the two collide.
    from . import reviewer as _rev
    vocab = dict(_rev._merged("reviewer_moods", _rev.DEFAULT_REV_MOOD))
    vocab.update(cfg["chat_moods"])
    moods = json.dumps(vocab)
    vconf = json.dumps(voice.settings(cfg))
    return """
<style>
html,body{margin:0;padding:0;background:%(ground)s;color:%(ink)s;
  font-family:system-ui,-apple-system,sans-serif;font-size:13px}
#amd-chat{display:flex;flex-direction:column;height:100vh}
#amd-face{position:relative;height:%(faceh)dpx;flex:none;overflow:hidden;
  border-bottom:2px solid %(edge)s;background:#000}
#amd-face img{position:absolute;left:50%%;bottom:0;height:112%%;width:auto;
  transform:translateX(-50%%);image-rendering:pixelated}
#amd-scan{position:absolute;inset:0;pointer-events:none;
  background:repeating-linear-gradient(180deg,rgba(0,0,0,.34) 0 1px,transparent 1px 3px)}
#amd-log{flex:1;overflow-y:auto;padding:10px 11px;line-height:1.55}
.amd-turn{margin:0 0 10px;white-space:pre-wrap;word-break:break-word}
.amd-turn.me{opacity:.72;border-left:2px solid %(edge)s;padding-left:8px}
.amd-turn.her{border-left:2px solid transparent;padding-left:8px}
#amd-status{flex:none;padding:5px 11px;font-size:11px;opacity:.6;min-height:16px}
</style>
<div id="amd-chat">
  <div id="amd-face"><img id="amd-img"><div id="amd-scan"></div></div>
  <div id="amd-log"></div>
  <div id="amd-status"></div>
</div>
<script>
%(voicejs)s
(function(){
  var PICS=%(face)s, MOODS=%(moods)s;
  var log=document.getElementById("amd-log"), img=document.getElementById("amd-img");
  var status=document.getElementById("amd-status");
  var V=amdVoice(%(vconf)s), live=null;

  function pick(a){return a[(Math.random()*a.length)|0]}
  function faceFor(mood){
    var order=MOODS[mood]||MOODS.normal||["normal"];
    for(var i=0;i<order.length;i++){var l=PICS[order[i]];if(l&&l.length)return pick(l)}
    var k=Object.keys(PICS);return k.length?pick(PICS[k[0]]):null;
  }
  function bottom(){log.scrollTop=log.scrollHeight}
  function row(cls){
    var d=document.createElement("div");d.className="amd-turn "+cls;
    log.appendChild(d);bottom();return d;
  }
  window.amdChat={
    mood:function(m){var s=faceFor(m);if(s)img.src=s},
    me:function(t){row("me").textContent=t},
    open:function(){live=row("her");V.open(live)},
    push:function(t){if(live){V.push(t);bottom()}},
    close:function(){V.close();live=null;bottom()},
    said:function(t){V.say(row("her"),t);bottom()},
    status:function(t){status.textContent=t||""},
    clear:function(){log.innerHTML="";status.textContent=""}
  };
  // Clicking finishes the line rather than waiting it out.
  document.getElementById("amd-log").addEventListener("click",function(){
    V.wake(); V.skip();
  });
  document.getElementById("amd-face").addEventListener("click",function(){
    V.wake(); pycmd("amd_chat_poke");
  });
  window.amdChat.mood("normal");
})();
</script>
""" % {"ground": ground, "ink": ink, "edge": edge, "face": face,
       "moods": moods, "voicejs": voice.JS, "vconf": vconf,
       "faceh": max(90, min(int(cfg.get("chat_face_height") or 220), 600))}


class ChatDock(QDockWidget):
    def __init__(self, parent):
        QDockWidget.__init__(self, TITLE, parent)
        self.setObjectName(DOCK_NAME)
        self.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea
                             | Qt.DockWidgetArea.LeftDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable
                         | QDockWidget.DockWidgetFeature.DockWidgetMovable
                         | QDockWidget.DockWidgetFeature.DockWidgetFloatable)

        self._turns: list[dict[str, str]] = []
        self._stop = threading.Event()
        self._busy = False
        self._head: MoodHead | None = None

        box = QWidget(self)
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        self.web = AnkiWebView(box, title="amadeus chat")
        self.web.set_bridge_command(self._on_js, self)
        lay.addWidget(self.web, 1)

        row = QHBoxLayout()
        row.setContentsMargins(6, 0, 6, 6)
        self.picker = QComboBox(box)
        self.picker.currentTextChanged.connect(self._pick_provider)
        row.addWidget(self.picker, 1)
        self.send_btn = QPushButton("Kirim", box)
        self.send_btn.clicked.connect(self._send)
        row.addWidget(self.send_btn)
        lay.addLayout(row)

        self.input = QPlainTextEdit(box)
        self.input.setPlaceholderText("Tanya apa saja…  (Ctrl+Enter kirim)")
        self.input.setMinimumHeight(70)
        self.input.setMaximumHeight(150)
        lay.addWidget(self.input)

        self.setWidget(box)
        self._render()

        sc = QShortcut(QKeySequence("Ctrl+Return"), self.input)
        sc.activated.connect(self._send)

    # ------------------------------------------------------------ rendering

    def _render(self):
        from . import pictures

        cfg = chatconf.load()
        pics = pictures()
        theme = (mw.addonManager.getConfig(chatconf.PACKAGE) or {}).get("theme", "vhs")
        self.web.stdHtml(_page(cfg, pics, theme), css=[], js=[],
                         context=self, default_css=False)
        names = chatconf.provider_names(cfg)
        self.picker.blockSignals(True)
        self.picker.clear()
        self.picker.addItems(names or ["(belum ada provider)"])
        active = chatconf.active_provider(cfg)
        if active and active["name"] in names:
            self.picker.setCurrentText(active["name"])
        self.picker.blockSignals(False)

    def _eval(self, js):
        try:
            self.web.eval(js)
        except Exception:
            pass

    def _say(self, fn, *args):
        self._eval("window.amdChat && amdChat.%s(%s)"
                   % (fn, ",".join(json.dumps(a) for a in args)))

    def _on_js(self, message):
        if message == "amd_chat_poke":
            self._say("mood", "happy")
        return False

    def _pick_provider(self, name):
        if name and not name.startswith("("):
            chatconf.save_active_provider(name)

    # ------------------------------------------------------------- sending

    def _send(self):
        if self._busy:
            self._stop.set()
            return
        text = self.input.toPlainText().strip()
        if not text:
            return
        cfg = chatconf.load()
        provider = chatconf.active_provider(cfg)
        if provider is None:
            showWarning("Belum ada provider di config Amadeus Deck.\n\n"
                        "Tambahkan satu di bawah \"providers\", lalu buka panel ini lagi.")
            return
        try:
            key = chatconf.resolve_api_key(provider)
        except chatconf.KeyLookupError as exc:
            showWarning(str(exc))
            return

        self.input.clear()
        self._say("me", text)
        self._turns.append({"role": "user", "content": text})

        system = chatconf.system_prompt(
            cfg, study_summary() if cfg["send_study_context"] else "")
        messages = self._history(cfg, text)

        self._busy = True
        self._stop.clear()
        self._head = MoodHead(cfg["chat_moods"])
        self.send_btn.setText("Stop")
        self._say("status", "%s memikirkan…" % provider["model"])
        self._say("open")
        reply: list[str] = []

        def on_text(delta):
            reply.append(delta)
            mood, shown = self._head.feed(delta)
            def apply():
                if mood:
                    self._say("mood", mood)
                if shown:
                    self._say("push", shown)
            mw.taskman.run_on_main(apply)

        def on_status(msg):
            mw.taskman.run_on_main(lambda: self._say("status", msg))

        def task():
            providers.stream_completion(
                provider, key, system, messages,
                max_tokens=cfg["max_tokens"], timeout=cfg["timeout_seconds"],
                on_text=on_text, on_status=on_status,
                should_stop=self._stop.is_set)

        def done(future):
            error = None
            try:
                future.result()
            except Exception as exc:      # noqa: BLE001 - shown to the user
                error = exc
            self._finish("".join(reply), error)

        mw.taskman.run_in_background(task, done)

    def _finish(self, whole, error):
        self._busy = False
        self.send_btn.setText("Kirim")
        left = self._head.flush() if self._head else ""
        if left:
            self._say("push", left)
        self._say("close")
        if error is not None:
            self._say("status", str(error)[:220])
            self._say("mood", "sad")
            return
        self._say("status", "")
        text = whole.strip()
        if text:
            # store what she said without the face tag, so the next turn's
            # history does not teach her to repeat it as literal text
            head = MoodHead([])
            _mood, body = head.feed(text)
            self._turns.append({"role": "assistant", "content": (body or text).strip()})

    def _history(self, cfg, text):
        out = []
        turns = max(0, int(cfg["max_history_turns"]))
        for turn in (self._turns[:-1][-turns * 2:] if turns else []):
            out.append(dict(turn))
        content = text
        if cfg["send_card_context"]:
            try:
                ctx = cardctx.current_context(cfg["max_context_chars"])
            except Exception:
                ctx = None
            if ctx is not None:
                summary = ctx.summary(cfg["max_context_chars"])
                if summary:
                    content = "Kartu yang sedang dibuka:\n%s\n\n%s" % (summary, text)
        out.append({"role": "user", "content": content})
        return out

    def closeEvent(self, event):
        self._stop.set()
        QDockWidget.closeEvent(self, event)


def react(mood, line):
    """Her reaction to an answered card, when the chat panel is the surface
    showing her. Two of her on screen at once -- a floating overlay and a panel
    -- is one too many, so whichever is open gets the reaction, not both.

    Returns whether the panel took it.
    """
    if _dock is None or not _dock.isVisible():
        return False
    _dock._say("mood", mood)
    if line:
        _dock._say("said", line)
    return True


def is_open():
    return _dock is not None and _dock.isVisible()


_dock: ChatDock | None = None


def toggle():
    global _dock
    cfg = chatconf.load()
    if not cfg["chat_enabled"]:
        tooltip("Chat Amadeus dimatikan di config.")
        return
    from . import pictures

    if not pictures():
        showWarning("Belum ada gambar karakter di folder character/.")
        return
    if _dock is None:
        _dock = ChatDock(mw)
        mw.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, _dock)
        width = max(280, min(int(cfg.get("chat_width") or 420), 1200))
        _dock.setMinimumWidth(280)
        _dock.resize(QSize(width, 760))
    _dock.setVisible(not _dock.isVisible())
    if _dock.isVisible():
        _dock.input.setFocus()
    _tell_reviewer(not _dock.isVisible())


def _tell_reviewer(show):
    """Hide the floating overlay while the panel is up, and bring it back when
    the panel goes away."""
    try:
        if mw.state == "review" and mw.reviewer and mw.reviewer.web:
            mw.reviewer.web.eval(
                "window.amdRevShow && amdRevShow(%s)" % ("true" if show else "false"))
    except Exception:
        pass


def register():
    from aqt.qt import QAction

    def setup():
        cfg = chatconf.load()
        act = QAction("Amadeus: buka chat", mw)
        keys = str(cfg.get("chat_shortcut") or "").strip()
        if keys:
            act.setShortcut(QKeySequence(keys))
        act.triggered.connect(lambda _=False: toggle())
        mw.form.menuTools.addAction(act)

    gui_hooks.main_window_did_init.append(setup)
