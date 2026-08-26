"""
The companion during review.

Nothing here touches note types or card templates. The portrait is appended to
the reviewer page inside a Shadow DOM, which means your card CSS (Kiku or
anything else) cannot reach in and style it, and none of this can leak out and
disturb your cards. Remove the add-on and your notes are exactly as they were.
"""

import json
import random

from . import grain, voice, warp
from . import theme as theme_mod

from aqt import gui_hooks, mw

DEFAULT_REV_LINES = {
    "good": ["Bagus.", "Itu baru benar.", "Hm. Bisa juga kamu.", "Tepat."],
    "easy": ["Kelewat gampang, ya?", "Oke, aku naikkan standarnya.",
             "Kalau semua semudah itu kita sudah selesai."],
    "hard": ["Susah? Tidak apa-apa.", "Pelan saja, yang penting benar.",
             "Kartu itu memang menyebalkan."],
    "wrong": ["Salah. Ingat baik-baik.", "Hmph. Ulangi.", "Tidak apa-apa. Sekali lagi."],
    "annoyed": ["Tiga kali berturut-turut. Fokus tidak?", "Serius, kartu ini lagi?",
                "Coba pelankan."],
    "pissed": ["Lima kali! Istirahat dulu sana.", "Kamu asal tekan, ya?",
               "Cukup. Tarik napas."],
    "poke": ["Apa? Aku sedang menghitung.", "Jangan dicolek terus.",
             "Kerjakan kartunya, bukan aku."],
    "idle": [""],          # present but quiet: no bubble while you read the card
}

DEFAULT_REV_MOOD = {
    "good": ["happy", "winking"],
    "easy": ["sided_pleasant", "winking", "happy"],
    "hard": ["sided_thinking", "normal"],
    "wrong": ["disappointed", "sad"],
    "annoyed": ["annoyed"],
    "pissed": ["pissed", "angry", "sided_angry"],
    "poke": ["sided_surprised", "blush", "annoyed"],
    "idle": ["normal", "indifferent", "sided_thinking"],
}

_again_run = 0


def _cfg():
    return mw.addonManager.getConfig(__name__.split(".")[0]) or {}


def _merged(key, fallback):
    """Same rule as the deck screen: config overrides one state at a time."""
    out = dict(fallback)
    user = _cfg().get(key)
    if isinstance(user, dict):
        for state, val in user.items():
            if isinstance(val, list):
                out[state] = val
    return out


def _chat_open():
    """Whether the chat panel is up. Imported late: chat imports this module."""
    try:
        from . import chat
        return chat.is_open()
    except Exception:
        return False


def _payload(addon, pics):
    c = _cfg()
    corner = c.get("reviewer_corner") or "bottom-right"
    return json.dumps({
        "pics": {m: ["/_addons/%s/character/%s" % (addon, n) for n in v]
                 for m, v in pics.items()},
        "moodFor": _merged("reviewer_moods", DEFAULT_REV_MOOD),
        "lines": _merged("reviewer_lines", DEFAULT_REV_LINES),
        "size": int(c.get("reviewer_size") or 190),
        "corner": corner,
        "hide": int(c.get("reviewer_hide_seconds") or 5),
        "always": bool(c.get("reviewer_always_visible", True)),
        "pal": theme_mod.palette(theme_mod.name_of(c)),
        "rot": theme_mod.rotations(theme_mod.name_of(c)),
        "grain": grain.settings(c),
        "warp": warp.settings(c),
        "effects": bool(c.get("effects", True)),
        "hidden": _chat_open(),
        "voice": voice.settings(c),
    })


SCRIPT = r"""
__VOICE__
__GRAIN__
__WARP__
(function(){
  if (window.__amdRev) return;
  var D = __PAYLOAD__;
  window.__amdRev = true;

  var reduce = window.matchMedia &&
               window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var fx = D.effects && !reduce;

  var host = document.createElement("div");
  host.id = "amd-rev-host";
  var corner = D.corner.split("-");
  host.setAttribute("style",
    "position:fixed!important;z-index:2147483600!important;" +
    corner[0] + ":14px!important;" + corner[1] + ":14px!important;" +
    "width:" + D.size + "px!important;height:" + Math.round(D.size * 1.28) +
    "px!important;pointer-events:auto!important;opacity:0;" +
    "transition:opacity .18s linear;");
  document.body.appendChild(host);

  // Shadow DOM: the card's own stylesheet cannot cross this boundary, so Kiku
  // (or any note type) stays untouched and unaffected either way.
  if (D.hidden) host.style.display = "none";
  // The panel and this overlay are the same character. Whichever is on screen
  // takes the reaction; both at once is one of her too many.
  window.amdRevShow = function(on){ host.style.display = on ? "" : "none"; };

  var root = host.attachShadow({mode: "open"});
  var P = D.pal, split = P.fx === "split";
  var thick = P.light ? "1px" : "2px";
  function tint(hex, a){
    var v = hex.replace("#", "");
    return "rgba(" + parseInt(v.slice(0,2),16) + "," + parseInt(v.slice(2,4),16)
         + "," + parseInt(v.slice(4,6),16) + "," + a + ")";
  }

  // A noise tile made once and repeated. Shipping a PNG would mean another
  // file to load through the add-on's web exports for no benefit.
  root.innerHTML =
    "<style>" +
    ":host{all:initial}" +
    ".w{position:relative;width:100%;height:100%;overflow:hidden;cursor:pointer;" +
      "font-family:system-ui,-apple-system,sans-serif;" +
      "background:" + P.card + ";" +
      "border:" + thick + " solid " + P.line + ";" +
      "display:flex;flex-direction:column;justify-content:flex-end}" +
    "img{position:absolute;left:50%;bottom:0;height:104%;width:auto;" +
      "max-width:none;transform:translateX(-50%);pointer-events:none}" +
    (split
      ? ".ghost{mix-blend-mode:screen;opacity:.5}" +
        ".r{filter:sepia(1) hue-rotate(-40deg) saturate(6) brightness(1.05)}" +
        ".c{filter:sepia(1) hue-rotate(150deg) saturate(6) brightness(1.05)}" +
        ".slice{display:none}" +
        (fx ? ".r{animation:sr 3.7s steps(1) infinite}" +
              ".c{animation:sc 3.7s steps(1) infinite}" : "")
      : ".base{filter:grayscale(1) sepia(1) hue-rotate(" + D.rot[0] + "deg) saturate(3.4) brightness(1.1);opacity:.92}" +
        ".ghost{display:none}" +
        ".slice{opacity:0;clip-path:inset(38% 0 46% 0);" +
          "filter:grayscale(1) sepia(1) hue-rotate(" + D.rot[1] + "deg) saturate(4) brightness(1.15);opacity:0}" +
        (fx ? ".slice{animation:sl 4.2s steps(1) infinite}" : "")) +
    "@keyframes sr{0%,88%{transform:translateX(-50%)}" +
      "90%{transform:translate(calc(-50% - 5px))}" +
      "94%{transform:translate(calc(-50% + 3px))}100%{transform:translateX(-50%)}}" +
    "@keyframes sc{0%,88%{transform:translateX(-50%)}" +
      "90%{transform:translate(calc(-50% + 5px))}" +
      "94%{transform:translate(calc(-50% - 3px))}100%{transform:translateX(-50%)}}" +
    "@keyframes sl{0%,72%{transform:translateX(-50%);opacity:0}" +
      "74%{transform:translate(calc(-50% + 9px));opacity:.9}" +
      "78%{transform:translate(calc(-50% - 7px));opacity:.9}" +
      "82%,100%{transform:translateX(-50%);opacity:0}}" +
    ".scan{position:absolute;inset:0;pointer-events:none;background:" +
      "repeating-linear-gradient(180deg,rgba(0,0,0,.34) 0 1px,transparent 1px 3px)}" +
    ".noise{position:absolute;inset:0;pointer-events:none;background-repeat:repeat}" +
    ".track{position:absolute;left:0;right:0;height:40px;pointer-events:none;" +
      "background:linear-gradient(180deg,transparent,rgba(255,255,255,.10) 45%,transparent);" +
      (fx ? "animation:ro 5.5s linear infinite" : "display:none") + "}" +
    "@keyframes ro{0%{top:-50%}100%{top:110%}}" +
    ".say{position:relative;z-index:3;padding:7px 9px;font-size:12px;line-height:1.45;" +
      "background:" + tint(P.ground, .9) + ";" +
      "color:" + P.ink + ";" +
      "border-top:" + thick + " solid " + P.edge + "}" +
    ".jolt img:not(.slice){animation:j .3s steps(2)}" +
    ".jolt .noise{opacity:.42}" +
    "@keyframes j{0%{transform:translate(calc(-50% - 7px))}" +
      "40%{transform:translate(calc(-50% + 6px))}100%{transform:translateX(-50%)}}" +
    "</style>" +
    "<div class='w'>" +
      "<img class='base'><img class='ghost r'><img class='ghost c'><img class='slice'>" +
      "<div class='scan'></div><div class='noise'></div><div class='track'></div>" +
      "<div class='say'></div></div>";

  var wrap = root.querySelector(".w");
  var imgs = root.querySelectorAll("img");
  var say = root.querySelector(".say");
  amdGrain(root.querySelector(".noise"), D.grain);
  var timer = null;

  function pick(a){ return a[(Math.random() * a.length) | 0]; }

  // The ordered list, not one at random: these are mouth positions and frame 1
  // is the shut one.
  function framesFor(mood){
    var order = D.moodFor[mood] || ["normal"];
    for (var i = 0; i < order.length; i++){
      var l = D.pics[order[i]];
      if (l && l.length) return l;
    }
    var k = Object.keys(D.pics);
    return k.length ? D.pics[k[0]] : [];
  }

  var V0 = D.voice || {};
  var BLINK = {on: V0.blink, min: V0.blinkMin, max: V0.blinkMax, hold: V0.blinkHold,
               closed: D.pics.eyes_closed || [], sided: D.pics.sided_eyes_closed || []};
  var WARP = amdWarp(wrap, imgs, D.warp || {});
  var MOUTH = amdMouth(function(src, how){
    (how === "mood" ? WARP.swap : WARP.set)(src);
  }, framesFor, V0.mouthMs, BLINK);
  MOUTH.blink();
  var V = amdVoice(D.voice || {}, (D.voice && D.voice.mouth) ? MOUTH : {});

  function settle(){
    // Back to a quiet face rather than vanishing, so she stays company for the
    // whole session instead of blinking in and out.
    if (D.always) { window.amdReact("idle", true); }
    else { host.style.opacity = "0"; }
  }

  window.amdReact = function(mood, quiet){
    MOUTH.set(mood);
    var pool = D.lines[mood];
    var text = pool ? pick(pool) : "";
    say.style.display = text ? "block" : "none";
    V.say(say, text);
    host.style.opacity = "1";
    if (fx && !quiet){
      wrap.classList.remove("jolt"); void wrap.offsetWidth; wrap.classList.add("jolt");
      setTimeout(function(){ wrap.classList.remove("jolt"); }, 340);
    }
    clearTimeout(timer);
    if (!quiet) timer = setTimeout(settle, D.hide * 1000);
  };

  wrap.addEventListener("click", function(){
    V.wake();
    // mid-sentence, a click finishes the line instead of discarding it
    if (V.skip()) return;
    window.amdReact("poke");
  });

  if (D.always) window.amdReact("idle", true);
})();
"""


def on_webview_content(web_content, context):
    import aqt.reviewer

    if not isinstance(context, aqt.reviewer.Reviewer):
        return
    package = __name__.split(".")[0]
    c = mw.addonManager.getConfig(package) or {}
    if not c.get("show_in_reviewer", True):
        return
    from . import pictures

    pics = pictures()
    if not pics:
        return
    script = (SCRIPT
              .replace("__PAYLOAD__", _payload(package, pics))
              .replace("__VOICE__", voice.JS)
              .replace("__GRAIN__", grain.JS)
              .replace("__WARP__", warp.JS))
    web_content.body += "<script>%s</script>" % script


def on_answer(reviewer, card, ease):
    global _again_run
    if ease == 1:
        _again_run += 1
        mood = "pissed" if _again_run >= 5 else ("annoyed" if _again_run >= 3 else "wrong")
    else:
        _again_run = 0
        mood = {2: "hard", 3: "good", 4: "easy"}.get(ease, "good")
    try:
        from . import chat

        if chat.is_open():
            pool = _merged("reviewer_lines", DEFAULT_REV_LINES).get(mood) or []
            chat.react(mood, random.choice(pool) if pool else "")
            return
    except Exception:
        pass
    try:
        reviewer.web.eval("window.amdReact && window.amdReact(%s)" % json.dumps(mood))
    except Exception:
        pass


def on_reviewer_end(*args):
    global _again_run
    _again_run = 0


def register():
    gui_hooks.webview_will_set_content.append(on_webview_content)
    gui_hooks.reviewer_did_answer_card.append(on_answer)
    gui_hooks.reviewer_will_end.append(on_reviewer_end)
