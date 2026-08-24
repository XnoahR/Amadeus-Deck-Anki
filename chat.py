# SPDX-License-Identifier: MIT
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
import os
import re
import threading
from typing import Any

from aqt import gui_hooks, mw
from aqt.qt import (
    QColor, QComboBox, QDockWidget, QKeySequence, QHBoxLayout, QPalette,
    QPlainTextEdit, QPushButton, QShortcut, QSize, Qt, QVBoxLayout, QWidget,
)
from aqt.utils import showWarning, tooltip
from aqt.webview import AnkiWebView

from . import cardctx, chatconf, grain, providers, voice
from . import theme as theme_mod

DOCK_NAME = "amadeusChatDock"
# Anki keeps user_files across add-on updates, which is the whole point: a
# conversation that vanishes on restart is what makes her feel like she does not
# know you.
STORE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "user_files", "chat.json")
SUMMARY = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "user_files", "chat-summary.txt")


# Japanese runs about one token per character; Latin script about a quarter of
# that. One ratio for both would be wrong by 4x on a mixed conversation, which
# is exactly what this add-on has.
_CJK = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff]")


def estimate_tokens(text):
    """Close enough to size a bar with. Nobody here needs the exact number, and
    getting it exactly would mean shipping a tokeniser per model."""
    if not text:
        return 0
    cjk = len(_CJK.findall(text))
    return int(cjk + (len(text) - cjk) / 3.6) + 1


class ThoughtFilter:
    """Drop the model's reasoning before anyone sees it.

    Some models narrate their thinking inline, wrapped in <thought> or <think>,
    and the OpenAI-compatible layer hands it over as ordinary content. Left
    alone it lands in the panel: three paragraphs of the model talking to itself
    about you, in front of you.

    The stream arrives in arbitrary pieces, so a tag routinely straddles two of
    them. Anything that could still turn into an opening tag is held back rather
    than emitted and regretted.
    """

    TAGS = (("<thought>", "</thought>"), ("<think>", "</think>"),
            ("<reasoning>", "</reasoning>"))

    def __init__(self):
        self.buf = ""
        self.closing = None

    def _safe_cut(self, text):
        """How much can be released without risking half a tag."""
        cut = text.rfind("<")
        if cut < 0:
            return len(text)
        tail = text[cut:]
        return cut if any(o.startswith(tail) for o, _c in self.TAGS) else len(text)

    def feed(self, delta):
        self.buf += delta or ""
        out = []
        while self.buf:
            if self.closing:
                at = self.buf.find(self.closing)
                if at < 0:
                    # still inside: throw the thinking away, but keep enough
                    # tail that a split closing tag is still recognisable
                    keep = len(self.closing) - 1
                    self.buf = self.buf[-keep:] if keep else ""
                    break
                self.buf = self.buf[at + len(self.closing):]
                self.closing = None
                continue

            found, opener, closer = None, None, None
            for open_tag, close_tag in self.TAGS:
                at = self.buf.find(open_tag)
                if at >= 0 and (found is None or at < found):
                    found, opener, closer = at, open_tag, close_tag
            if found is None:
                cut = self._safe_cut(self.buf)
                out.append(self.buf[:cut])
                self.buf = self.buf[cut:]
                break
            out.append(self.buf[:found])
            self.buf = self.buf[found + len(opener):]
            self.closing = closer
        return "".join(out)

    def flush(self):
        """Whatever was held back, unless the model stopped mid-thought."""
        if self.closing:
            self.buf = ""
            return ""
        out, self.buf = self.buf, ""
        return out


class MoodHead:
    """She is asked to open with a face tag. Hold the first few characters back
    until it can be recognised, so it never flickers on screen before it gets
    stripped, and release everything held back if it never comes.

    Both bracket shapes are accepted because models pick one and stick to it,
    and which one is not something a prompt reliably decides. They are not
    treated the same, though: `[...]` is unambiguous enough to strip whatever is
    inside, while `(...)` is ordinary punctuation, so it is only taken as a tag
    when it names a mood we actually have. Otherwise an opening aside -- "(Ya,
    lagi.) Kartunya..." -- would silently lose its first clause.
    """

    LIMIT = 40
    PAIRS = {"[": "]", "(": ")", "\uff08": "\uff09", "\u3010": "\u3011"}

    def __init__(self, allowed):
        self.allowed = {str(a).strip().lower() for a in allowed}
        self.buf = ""
        self.done = False

    def _release(self):
        out, self.buf, self.done = self.buf, "", True
        return None, out

    def feed(self, delta):
        """-> (mood or None, text to display)"""
        if self.done:
            return None, delta
        self.buf += delta
        head = self.buf.lstrip()
        if not head:
            return None, ""

        shut = self.PAIRS.get(head[0])
        if shut is None:
            return self._release()

        close = head.find(shut)
        if close < 0:
            if len(head) > self.LIMIT:      # not a tag after all
                return self._release()
            return None, ""                 # still waiting for the rest

        name = head[1:close].strip().lower()
        known = name in self.allowed
        if head[0] != "[" and not known:
            # a real parenthesis, not a face tag
            return self._release()

        self.done = True
        self.buf = ""
        return (name if known else None), head[close + 1:].lstrip()

    def flush(self):
        out, self.buf, self.done = self.buf, "", True
        return out


def load_turns():
    try:
        with open(STORE, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    out = []
    for t in data:
        if not isinstance(t, dict) or t.get("role") not in ("user", "assistant"):
            continue
        if not isinstance(t.get("content"), str):
            continue
        turn = {"role": t["role"], "content": t["content"]}
        if isinstance(t.get("mood"), str):
            turn["mood"] = t["mood"]
        out.append(turn)
    return out


def save_turns(turns, keep):
    """Kept as plain JSON beside the add-on, on purpose: a memory you cannot
    open and read is one you cannot correct."""
    try:
        os.makedirs(os.path.dirname(STORE), exist_ok=True)
        with open(STORE, "w", encoding="utf-8") as fh:
            json.dump(turns[-max(2, int(keep)):], fh, ensure_ascii=False, indent=1)
    except OSError:
        pass


def forget_turns():
    for path in (STORE, SUMMARY):
        try:
            os.remove(path)
        except OSError:
            pass


def load_summary():
    try:
        with open(SUMMARY, encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return ""


def save_summary(text):
    try:
        os.makedirs(os.path.dirname(SUMMARY), exist_ok=True)
        with open(SUMMARY, "w", encoding="utf-8") as fh:
            fh.write((text or "").strip())
    except OSError:
        pass


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


def _qss(theme):
    """The input row is Qt, not the web view, so none of the page's styling
    reaches it -- it sits under the panel in Anki's default grey looking like it
    belongs to a different program. Same six colours, applied by hand."""
    c = theme_mod.palette(theme)
    return """
QWidget{background:%(ground)s;color:%(ink)s}
QPlainTextEdit{background:%(card)s;color:%(ink)s;border:1px solid %(line)s;
  border-left:2px solid %(edge)s;padding:6px 8px;selection-background-color:%(edge)s;
  selection-color:%(ground)s}
QPlainTextEdit:focus{border-color:%(edge)s}
QPushButton{background:%(card)s;color:%(ink)s;border:1px solid %(line)s;
  padding:5px 13px;font-size:12px}
QPushButton:hover{border-color:%(edge)s;color:%(edge)s}
QPushButton:pressed{background:%(edge)s;color:%(ground)s}
QComboBox{background:%(card)s;color:%(ink)s;border:1px solid %(line)s;
  padding:4px 8px;font-size:12px}
QComboBox:hover{border-color:%(edge)s}
QComboBox::drop-down{border:0;width:18px}
QComboBox::down-arrow{image:none;border-left:4px solid transparent;
  border-right:4px solid transparent;border-top:5px solid %(dim)s;
  width:0;height:0;margin-right:6px}
QComboBox QAbstractItemView{background:%(card)s;color:%(ink)s;
  border:1px solid %(line)s;selection-background-color:%(edge)s;
  selection-color:%(ground)s;outline:0}
QToolTip{background:%(card)s;color:%(ink)s;border:1px solid %(edge)s;padding:3px}
""" % c


def _page(cfg, pics, theme):
    c = theme_mod.palette(theme)
    ink, edge, ground = c["ink"], c["edge"], c["ground"]
    card, line, dim = c["card"], c["line"], c["dim"]
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
    her, _you = chatconf.who(cfg)
    return """
<style>
html,body{margin:0;padding:0;background:%(ground)s;color:%(ink)s;
  font-family:system-ui,-apple-system,sans-serif;font-size:13px}
#amd-chat{display:flex;flex-direction:column;height:100vh;position:relative}
/* Grain belongs to the picture, not to the page. Over the message log it is
   just something between you and the words you are reading. */
#amd-grain{position:absolute;inset:0;pointer-events:none;z-index:2;
  background-repeat:repeat}
#amd-face{position:relative;height:%(faceh)dpx;flex:none;overflow:hidden;
  border-bottom:2px solid %(edge)s;background:#000}
#amd-face img{position:absolute;left:50%%;bottom:0;height:112%%;width:auto;
  transform:translateX(-50%%)}
#amd-scan{position:absolute;inset:0;pointer-events:none;
  background:repeating-linear-gradient(180deg,rgba(0,0,0,.34) 0 1px,transparent 1px 3px)}
#amd-log{flex:1;overflow-y:auto;padding:12px 13px;line-height:1.58}
#amd-log::-webkit-scrollbar{width:8px}
#amd-log::-webkit-scrollbar-thumb{background:%(line)s}
.amd-turn{margin:0 0 12px;word-break:break-word}
.amd-turn.her{display:flex;gap:9px;align-items:flex-start}
/* The expression she wore for this line, kept next to it: scrolling back
   should show the mood she was in, not the mood she is in now. */
.amd-thumb{flex:none;width:38px;height:38px;border:1px solid %(line)s;
  background:#000 no-repeat;background-size:%(zoom)d%% auto;
  background-position:50%% %(thumby)d%%}
.amd-card{flex:1;background:%(card)s;border:1px solid %(line)s;
  border-left:2px solid %(edge)s;padding:8px 11px;white-space:pre-wrap}
.amd-name{font-size:10px;letter-spacing:.13em;color:%(edge)s;margin-bottom:3px}
.amd-turn.me{text-align:right}
.amd-turn.me span{display:inline-block;max-width:78%%;text-align:left;
  color:%(dim)s;border:1px dashed %(line)s;padding:6px 10px;white-space:pre-wrap}
#amd-status{flex:none;padding:5px 11px;font-size:11px;color:%(dim)s;min-height:16px}
#amd-meter{flex:none;display:flex;align-items:center;gap:8px;padding:6px 11px 0;
  font-size:10.5px;color:%(dim)s;cursor:default}
#amd-bar{flex:1;height:3px;background:%(line)s;position:relative;overflow:hidden}
#amd-bar i{position:absolute;inset:0 auto 0 0;width:0;background:%(edge)s;
  transition:width .3s linear}
#amd-meter.warm #amd-bar i{background:#ffb200}
#amd-meter.hot #amd-bar i{background:#ff3b30}
#amd-meter b{font-weight:600;font-variant-numeric:tabular-nums;color:%(ink)s}
</style>
<div id="amd-chat">
  <div id="amd-face"><img id="amd-img"><div id="amd-grain"></div>
    <div id="amd-scan"></div></div>
  <div id="amd-log"></div>
  <div id="amd-meter" title=""><span>konteks</span>
    <div id="amd-bar"><i></i></div><b></b></div>
  <div id="amd-status"></div>
</div>
<script>
%(voicejs)s
%(grainjs)s
(function(){
  var PICS=%(face)s, MOODS=%(moods)s, NAME=%(name)s, THUMBMOOD=%(thumbmood)s;
  var log=document.getElementById("amd-log"), img=document.getElementById("amd-img");
  var status=document.getElementById("amd-status");
  var VC=%(vconf)s;
  amdGrain(document.getElementById("amd-grain"), %(grain)s);

  function pick(a){return a[(Math.random()*a.length)|0]}
  // The whole ordered list, not one at random: the three pictures behind an
  // expression are mouth positions, and frame 1 is the shut one.
  function framesFor(mood){
    var order=MOODS[mood]||MOODS.normal||["normal"];
    for(var i=0;i<order.length;i++){var l=PICS[order[i]];if(l&&l.length)return l}
    var k=Object.keys(PICS);return k.length?PICS[k[0]]:[];
  }
  var MOUTH=amdMouth(function(src){img.src=src},framesFor,VC.mouthMs);
  var V=amdVoice(VC, VC.mouth?MOUTH:{}), live=null, liveThumb=null;

  function bottom(){log.scrollTop=log.scrollHeight}

  function mine(text){
    var d=document.createElement("div"); d.className="amd-turn me";
    var s=document.createElement("span"); s.textContent=text;
    d.appendChild(s); log.appendChild(d); bottom();
  }
  function hers(mood){
    var d=document.createElement("div"); d.className="amd-turn her";
    var th=document.createElement("div"); th.className="amd-thumb";
    var f=framesFor(THUMBMOOD?mood:"normal");
    if(f.length) th.style.backgroundImage="url("+f[0]+")";
    var card=document.createElement("div"); card.className="amd-card";
    var nm=document.createElement("div"); nm.className="amd-name"; nm.textContent=NAME;
    var body=document.createElement("div");
    card.appendChild(nm); card.appendChild(body);
    d.appendChild(th); d.appendChild(card); log.appendChild(d); bottom();
    return {body:body, thumb:th};
  }

  window.amdChat={
    mood:function(m){
      MOUTH.set(m);
      // The face tag arrives after the line has already opened, so the row's
      // own thumbnail is corrected the moment we learn it.
      if(liveThumb&&THUMBMOOD){var f=framesFor(m);
        if(f.length) liveThumb.style.backgroundImage="url("+f[0]+")"}
    },
    me:function(t){mine(t)},
    open:function(){var r=hers("normal");live=r.body;liveThumb=r.thumb;V.open(live)},
    push:function(t){if(live){V.push(t);bottom()}},
    close:function(){V.close();live=null;liveThumb=null;bottom()},
    said:function(t,mood){var r=hers(mood||"normal");V.say(r.body,t);bottom()},
    past:function(role,t,mood){
      if(role==="user"){mine(t)} else {hers(mood||"normal").body.textContent=t;}
      bottom();
    },
    status:function(t){status.textContent=t||""},
    context:function(d){
      var m=document.getElementById("amd-meter");
      var bar=m.querySelector("i"), num=m.querySelector("b");
      var pct=d.window?Math.min(100,d.total/d.window*100):0;
      bar.style.width=pct+"%%";
      m.classList.toggle("warm",pct>=60&&pct<85);
      m.classList.toggle("hot",pct>=85);
      num.textContent=d.window
        ? d.total.toLocaleString("id")+" / "+d.window.toLocaleString("id")
          +"  ("+(pct<0.1?"<0,1":pct.toFixed(1).replace(".",","))+"%%)"
        : "~"+d.total.toLocaleString("id")+" token";
      m.title=d.detail||"";
    },
    clear:function(){log.innerHTML="";status.textContent="";live=null;liveThumb=null}
  };
  log.addEventListener("click",function(){V.wake();V.skip()});
  document.getElementById("amd-face").addEventListener("click",function(){
    V.wake(); pycmd("amd_chat_poke");
  });
  window.amdChat.mood("normal");
})();
</script>
""" % {"ground": ground, "ink": ink, "edge": edge, "face": face, "card": card,
       "line": line, "dim": dim, "moods": moods, "voicejs": voice.JS,
       "vconf": vconf, "name": json.dumps(her.upper()),
       "faceh": max(90, min(int(cfg.get("chat_face_height") or 220), 600)),
       "zoom": max(100, min(int(cfg.get("chat_thumb_zoom") or 240), 800)),
       "thumby": max(0, min(int(cfg.get("chat_thumb_y") or 20), 100)),
       "thumbmood": "true" if cfg.get("chat_thumb_expression", True) else "false",
       "grain": json.dumps(grain.settings(cfg)),
       "grainjs": grain.JS}


def measure(cfg, turns, summary=""):
    """What the next request will roughly weigh, broken up so the panel can say
    where the weight is rather than just that there is some."""
    system = chatconf.system_prompt(
        cfg, study_summary() if cfg["send_study_context"] else "", summary)
    keep = max(0, int(cfg["max_history_turns"])) * 2
    history = turns[-keep:] if keep else []
    parts = {
        "system": estimate_tokens(system),
        "riwayat": sum(estimate_tokens(t.get("content", "")) for t in history),
        "kartu": estimate_tokens("x" * int(cfg["max_context_chars"]))
                 if cfg["send_card_context"] else 0,
    }
    parts["total"] = sum(parts.values())
    parts["pesan"] = len(history)
    return parts


class ChatDock(QDockWidget):
    def __init__(self, parent):
        QDockWidget.__init__(self, chatconf.who(chatconf.load())[0], parent)
        self.setObjectName(DOCK_NAME)
        self.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea
                             | Qt.DockWidgetArea.LeftDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable
                         | QDockWidget.DockWidgetFeature.DockWidgetMovable
                         | QDockWidget.DockWidgetFeature.DockWidgetFloatable)

        self._turns: list[dict[str, str]] = load_turns()
        self._stop = threading.Event()
        self._busy = False
        self._head: MoodHead | None = None
        self._thoughts = ThoughtFilter()
        self._mood = "normal"
        self._moods: Any = {}
        self._summary = load_summary()
        self._compacting = False

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
        self.forget_btn = QPushButton("Lupakan", box)
        self.forget_btn.setToolTip("Hapus percakapan yang tersimpan")
        self.forget_btn.clicked.connect(self._forget)
        row.addWidget(self.forget_btn)
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
        theme = theme_mod.name_of(mw.addonManager.getConfig(chatconf.PACKAGE) or {})
        self.setWindowTitle(chatconf.who(cfg)[0])
        self.setStyleSheet(_qss(theme))
        pal = self.input.palette()
        # Qt style sheets cannot reach the placeholder on a QPlainTextEdit, so
        # it stays black-on-dark unless the palette role is set directly.
        pal.setColor(QPalette.ColorRole.PlaceholderText,
                     QColor(theme_mod.palette(theme)["dim"]))
        self.input.setPalette(pal)
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
        if cfg["remember_chat"]:
            for turn in self._turns[-int(cfg["remember_messages"]):]:
                self._say("past", turn["role"], turn["content"],
                          turn.get("mood") or "normal")
        self._update_meter(cfg)

    def _eval(self, js):
        try:
            self.web.eval(js)
        except Exception:
            pass

    def _say(self, fn, *args):
        self._eval("window.amdChat && amdChat.%s(%s)"
                   % (fn, ",".join(json.dumps(a) for a in args)))

    def _update_meter(self, cfg=None):
        cfg = cfg or chatconf.load()
        provider = chatconf.active_provider(cfg) or {}
        try:
            window = max(0, int(provider.get("context_window") or 0))
        except (TypeError, ValueError):
            window = 0
        parts = measure(cfg, self._turns, self._summary)
        detail = ("system %d  ·  riwayat %d (%d pesan)  ·  kartu %d"
                  % (parts["system"], parts["riwayat"], parts["pesan"],
                     parts["kartu"]))
        if self._summary:
            detail += "  ·  ringkasan aktif"
        if not window:
            detail += "\nJendela model belum diisi (context_window di config)."
        self._say("context", {"total": parts["total"], "window": window,
                              "detail": detail})

    def _on_js(self, message):
        if message == "amd_chat_poke":
            self._say("mood", "happy")
        return False

    def _compact(self, cfg):
        """Fold the turns that are about to fall out of the window into a few
        sentences, instead of letting them vanish.

        Trimming by count is lossless right up until it is not: the twenty-first
        message back is simply gone, and she has no idea it existed. This costs
        one extra request, runs after the reply rather than in front of it, and
        never blocks anyone.
        """
        if self._busy or self._compacting:
            return
        keep = max(0, int(cfg["max_history_turns"])) * 2
        if not keep or len(self._turns) <= keep + 4:
            return
        dropping = self._turns[:-keep]
        provider = chatconf.active_provider(cfg)
        if provider is None:
            return
        try:
            key = chatconf.resolve_api_key(provider)
        except chatconf.KeyLookupError:
            return
        if not key:
            return

        talk = "\n".join("%s: %s" % ("Dia" if t["role"] == "user" else "Kamu",
                                      t["content"]) for t in dropping)
        ask = ("Ringkas percakapan berikut jadi paling banyak 3 kalimat, dalam "
               "bahasa yang sama. Simpan hanya yang berguna diingat nanti: "
               "keputusan, kebiasaan, dan hal yang dia sebut tentang dirinya. "
               "Buang basa-basi. Tulis ringkasannya saja.")
        if self._summary:
            ask += "\n\nRingkasan yang sudah ada, gabungkan:\n" + self._summary
        chunks = []
        self._compacting = True

        def work():
            providers.stream_completion(
                provider, key, ask, [{"role": "user", "content": talk}],
                max_tokens=300, timeout=int(cfg["timeout_seconds"]),
                on_text=chunks.append, on_status=lambda _c: None,
                should_stop=lambda: False)

        def done(future):
            self._compacting = False
            try:
                future.result()
            except Exception:
                return          # keep the turns; try again next time
            filt = ThoughtFilter()
            text = (filt.feed("".join(chunks)) + filt.flush()).strip()
            if not text:
                return
            self._summary = text
            save_summary(text)
            self._turns = self._turns[-keep:]
            if cfg["remember_chat"]:
                save_turns(self._turns, cfg["remember_messages"])
            self._update_meter(cfg)
            tooltip("Percakapan lama diringkas.", period=4000)

        mw.taskman.run_in_background(work, done)

    def _forget(self):
        self._turns = []
        self._summary = ""
        forget_turns()
        self._say("clear")
        tooltip("Percakapan dilupakan.")

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
        if not key:
            # The one moment a non-technical person is certainly stuck, so this
            # points at the guide instead of letting the provider answer with
            # an HTTP status.
            from . import settings

            showWarning("Belum ada API key untuk \"%s\".\n\n"
                        "Panduannya akan dibuka di browser." % provider["name"])
            settings.open_guide()
            return

        self.input.clear()
        self._say("me", text)
        self._turns.append({"role": "user", "content": text})

        her = chatconf.who(cfg)[0]
        system = chatconf.system_prompt(
            cfg, study_summary() if cfg["send_study_context"] else "",
            self._summary)
        messages = self._history(cfg, text)

        self._busy = True
        self._stop.clear()
        self._moods = cfg["chat_moods"]
        self._head = MoodHead(self._moods)
        self._thoughts = ThoughtFilter()
        self._mood = "normal"
        self.send_btn.setText("Stop")
        self._say("status", "%s sedang berpikir…" % her)
        self._say("open")
        reply: list[str] = []

        def on_text(delta):
            # Reasoning is stripped before anything else looks at the text: the
            # face tag comes after it, and history should not carry it either.
            visible = self._thoughts.feed(delta)
            if not visible:
                return
            reply.append(visible)
            mood, shown = self._head.feed(visible)
            def apply():
                if mood:
                    self._mood = mood
                    self._say("mood", mood)
                if shown:
                    self._say("push", shown)
            mw.taskman.run_on_main(apply)

        def on_status(code):
            said = {
                "thinking": "%s sedang berpikir…" % her,
                "truncated": "Jawabannya kepanjangan dan terpotong — naikkan "
                             "max_tokens di config lanjutan.",
            }.get(code, code)
            mw.taskman.run_on_main(lambda: self._say("status", said))

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
        tail = self._thoughts.flush()
        if tail:
            whole += tail
            _mood, shown = self._head.feed(tail) if self._head else (None, tail)
            if shown:
                self._say("push", shown)
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
            # Store what she said without the face tag, so the next turn's
            # history does not teach her to repeat it as literal text. The same
            # mood list as the live parse, or a "(normal)" opener would survive
            # into history while being stripped on screen.
            strip = MoodHead(self._moods or [])
            _mood, body = strip.feed(text)
            body += strip.flush()
            self._turns.append({"role": "assistant",
                                "content": (body or text).strip(),
                                "mood": self._mood})
        cfg = chatconf.load()
        if cfg["remember_chat"]:
            save_turns(self._turns, cfg["remember_messages"])
        self._update_meter(cfg)
        if cfg.get("compact_history"):
            self._compact(cfg)

    def _history(self, cfg, text):
        out = []
        turns = max(0, int(cfg["max_history_turns"]))
        for turn in (self._turns[:-1][-turns * 2:] if turns else []):
            # role and content only: the mood is ours for drawing her face, and
            # a stray field is rejected outright by some providers.
            out.append({"role": turn["role"], "content": turn["content"]})
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
        _dock._say("said", line, mood)
    return True


def is_open():
    return _dock is not None and _dock.isVisible()


_dock: ChatDock | None = None


def toggle():
    global _dock
    cfg = chatconf.load()
    if not cfg["chat_enabled"]:
        tooltip("Chat %s dimatikan di config." % chatconf.who(cfg)[0])
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
        act = QAction("%s: buka chat" % chatconf.who(cfg)[0], mw)
        keys = str(cfg.get("chat_shortcut") or "").strip()
        if keys:
            act.setShortcut(QKeySequence(keys))
        act.triggered.connect(lambda _=False: toggle())
        mw.form.menuTools.addAction(act)

    gui_hooks.main_window_did_init.append(setup)
