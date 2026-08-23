"""
The companion during review.

Nothing here touches note types or card templates. The portrait is appended to
the reviewer page inside a Shadow DOM, which means your card CSS (Kiku or
anything else) cannot reach in and style it, and none of this can leak out and
disturb your cards. Remove the add-on and your notes are exactly as they were.
"""

import json

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
        "theme": "holo" if c.get("theme") == "holo" else "vhs",
        "effects": bool(c.get("effects", True)),
    })


SCRIPT = r"""
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
  var root = host.attachShadow({mode: "open"});
  var vhs = D.theme === "vhs";

  // A noise tile made once and repeated. Shipping a PNG would mean another
  // file to load through the add-on's web exports for no benefit.
  var noiseUrl = "";
  if (fx) {
    var N = 64, cv = document.createElement("canvas");
    cv.width = cv.height = N;
    var cx = cv.getContext("2d"), id = cx.createImageData(N, N);
    for (var i = 0; i < id.data.length; i += 4) {
      var v = (Math.random() * 255) | 0;
      id.data[i] = id.data[i+1] = id.data[i+2] = v;
      id.data[i+3] = 255;
    }
    cx.putImageData(id, 0, 0);
    noiseUrl = cv.toDataURL("image/png");
  }

  root.innerHTML =
    "<style>" +
    ":host{all:initial}" +
    ".w{position:relative;width:100%;height:100%;overflow:hidden;cursor:pointer;" +
      "font-family:system-ui,-apple-system,sans-serif;" +
      "background:" + (vhs ? "#151020" : "#0f1722") + ";" +
      "border:" + (vhs ? "2px solid #2b1f3d" : "1px solid #1d3448") + ";" +
      "display:flex;flex-direction:column;justify-content:flex-end}" +
    "img{position:absolute;left:50%;bottom:0;height:104%;width:auto;" +
      "max-width:none;transform:translateX(-50%);pointer-events:none}" +
    (vhs
      ? ".ghost{mix-blend-mode:screen;opacity:.5}" +
        ".r{filter:sepia(1) hue-rotate(-40deg) saturate(6) brightness(1.05)}" +
        ".c{filter:sepia(1) hue-rotate(150deg) saturate(6) brightness(1.05)}" +
        ".slice{display:none}" +
        (fx ? ".r{animation:sr 3.7s steps(1) infinite}" +
              ".c{animation:sc 3.7s steps(1) infinite}" : "")
      : ".base{filter:grayscale(1) sepia(1) hue-rotate(155deg) saturate(3.4) brightness(1.1);opacity:.92}" +
        ".ghost{display:none}" +
        ".slice{clip-path:inset(38% 0 46% 0);" +
          "filter:grayscale(1) sepia(1) hue-rotate(255deg) saturate(4) brightness(1.15);opacity:0}" +
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
    ".noise{position:absolute;inset:0;pointer-events:none;opacity:.16;" +
      "mix-blend-mode:overlay;background-repeat:repeat;" +
      (noiseUrl ? "background-image:url(" + noiseUrl + ");" : "") +
      (fx ? "animation:cr .6s steps(3) infinite" : "") + "}" +
    "@keyframes cr{0%{background-position:0 0}33%{background-position:-14px 9px}" +
      "66%{background-position:11px -7px}100%{background-position:0 0}}" +
    ".track{position:absolute;left:0;right:0;height:40px;pointer-events:none;" +
      "background:linear-gradient(180deg,transparent,rgba(255,255,255,.10) 45%,transparent);" +
      (fx ? "animation:ro 5.5s linear infinite" : "display:none") + "}" +
    "@keyframes ro{0%{top:-50%}100%{top:110%}}" +
    ".say{position:relative;z-index:3;padding:7px 9px;font-size:12px;line-height:1.45;" +
      "background:" + (vhs ? "rgba(13,11,18,.9)" : "rgba(8,13,20,.88)") + ";" +
      "color:" + (vhs ? "#f2ecff" : "#d9e8f7") + ";" +
      "border-top:" + (vhs ? "2px solid #ff2d55" : "1px solid #35d6ff") + "}" +
    ".jolt img{animation:j .3s steps(2)}" +
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
  var timer = null;

  function pick(a){ return a[(Math.random() * a.length) | 0]; }

  function picFor(mood){
    var order = D.moodFor[mood] || ["normal"];
    for (var i = 0; i < order.length; i++){
      var l = D.pics[order[i]];
      if (l && l.length) return pick(l);
    }
    var k = Object.keys(D.pics);
    return k.length ? pick(D.pics[k[0]]) : null;
  }

  function settle(){
    // Back to a quiet face rather than vanishing, so she stays company for the
    // whole session instead of blinking in and out.
    if (D.always) { window.amdReact("idle", true); }
    else { host.style.opacity = "0"; }
  }

  window.amdReact = function(mood, quiet){
    var src = picFor(mood);
    if (src) { for (var i = 0; i < imgs.length; i++) imgs[i].src = src; }
    var pool = D.lines[mood];
    var text = pool ? pick(pool) : "";
    say.textContent = text;
    say.style.display = text ? "block" : "none";
    host.style.opacity = "1";
    if (fx && !quiet){
      wrap.classList.remove("jolt"); void wrap.offsetWidth; wrap.classList.add("jolt");
      setTimeout(function(){ wrap.classList.remove("jolt"); }, 340);
    }
    clearTimeout(timer);
    if (!quiet) timer = setTimeout(settle, D.hide * 1000);
  };

  wrap.addEventListener("click", function(){ window.amdReact("poke"); });

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
    web_content.body += "<script>%s</script>" % SCRIPT.replace(
        "__PAYLOAD__", _payload(package, pics))


def on_answer(reviewer, card, ease):
    global _again_run
    if ease == 1:
        _again_run += 1
        mood = "pissed" if _again_run >= 5 else ("annoyed" if _again_run >= 3 else "wrong")
    else:
        _again_run = 0
        mood = {2: "hard", 3: "good", 4: "easy"}.get(ease, "good")
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
