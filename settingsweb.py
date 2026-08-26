"""The settings form as a page instead of a stack of Qt widgets.

Qt can be themed, but only so far: the moment a stylesheet touches
`QCheckBox::indicator`, Qt drops the platform's own painter and the tick
disappears unless every state is drawn by hand. Rendering the form as HTML
sidesteps that entirely and gives the dialog the same visual language as the
panels it configures.

What does *not* move here is the raw JSON editor -- that is Anki's, and it stays
Anki's. This page writes the same config the Qt form did, key for key.
"""
from __future__ import annotations

import json
import os
from typing import Any

from aqt import mw
from aqt.qt import QDialog, QVBoxLayout
from aqt.utils import tooltip
from aqt.webview import AnkiWebView

from . import chatconf
from . import theme as theme_mod

PACKAGE = chatconf.PACKAGE


def _esc(text: Any) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _rows_html(fields, raw):
    """One tab's worth of rows. The spec is the same tuple list the Qt form
    used, so both describe the settings identically and neither can drift."""
    out = []
    for spec in fields:
        key, label, kind = spec[0], spec[1], spec[2]
        args = spec[3:]
        if kind == "head":
            out.append('<h4>%s</h4>' % _esc(label))
            continue
        if kind == "note":
            out.append('<p class="note">%s</p>' % _esc(label))
            continue
        if kind == "provider":
            out.append('<div id="prov"></div>')
            continue
        val = raw.get(key)
        if kind == "bool":
            out.append(
                '<div class="r"><label for="f_%s">%s</label>'
                '<div class="sw%s" id="f_%s" data-k="%s" data-t="bool" tabindex="0"'
                ' role="switch" aria-checked="%s"><i></i></div></div>'
                % (key, _esc(label), " on" if val else "", key, key,
                   "true" if val else "false"))
        elif kind in ("int", "float"):
            lo, hi = (args + (None, None))[:2]
            step = args[2] if len(args) > 2 else (1 if kind == "int" else 0.05)
            out.append(
                '<div class="r"><label for="f_%s">%s</label>'
                '<input id="f_%s" data-k="%s" data-t="%s" type="number"'
                ' value="%s" min="%s" max="%s" step="%s"></div>'
                % (key, _esc(label), key, key, kind, _esc(val),
                   _esc(lo), _esc(hi), _esc(step)))
        elif kind == "choice":
            opts = args[0] if args else None
            if opts is None:
                opts = theme_mod.choices()
            picks = "".join(
                '<option value="%s"%s>%s</option>'
                % (_esc(v), " selected" if v == val else "", _esc(t))
                for v, t in opts)
            out.append('<div class="r"><label for="f_%s">%s</label>'
                       '<select id="f_%s" data-k="%s" data-t="choice">%s</select></div>'
                       % (key, _esc(label), key, key, picks))
        elif kind == "longtext":
            out.append('<div class="long"><label for="f_%s">%s</label>'
                       '<textarea id="f_%s" data-k="%s" data-t="text" rows="6">%s</textarea></div>'
                       % (key, _esc(label), key, key, _esc(val or "")))
        else:
            out.append('<div class="r"><label for="f_%s">%s</label>'
                       '<input id="f_%s" data-k="%s" data-t="text" type="text"'
                       ' class="wide" value="%s"></div>'
                       % (key, _esc(label), key, key, _esc(val or "")))
    return "\n".join(out)


CSS = """
*{box-sizing:border-box}
html,body{margin:0;height:100%%;background:%(ground)s;color:%(ink)s;
  font-family:system-ui,-apple-system,"Segoe UI",sans-serif;font-size:13px}
body{display:flex;flex-direction:column;overflow:hidden}
.tabs{display:flex;gap:2px;padding:9px 12px 0;flex:none;flex-wrap:wrap}
.tabs button{font:inherit;font-size:12.5px;padding:8px 15px;color:%(dim)s;
  background:%(ground)s;border:1px solid %(line)s;border-bottom:none;cursor:pointer}
.tabs button.on{background:%(card)s;color:%(ink)s;border-bottom:2px solid %(edge)s;
  margin-bottom:-1px}
.body{flex:1;overflow-y:auto;background:%(card)s;border:1px solid %(line)s;
  margin:0 12px;padding:15px 18px}
.pane{display:none}.pane.on{display:block}
h4{margin:22px 0 9px;font-size:10.5px;letter-spacing:1.4px;color:%(edge)s;
  text-transform:uppercase;border-bottom:1px solid %(line)s;padding-bottom:5px;
  font-weight:700}
h4:first-child{margin-top:0}
.r{display:flex;align-items:center;gap:14px;margin:10px 0;min-height:26px}
.r label{flex:1;line-height:1.45}
.long{margin:12px 0}
.long label{display:block;margin-bottom:5px}
.long textarea{width:100%%;resize:vertical}
input,select,textarea{background:%(ground)s;color:%(ink)s;border:1px solid %(line)s;
  padding:5px 7px;font:inherit;font-size:12.5px;width:118px}
input.wide{width:220px}
textarea{width:100%%;font-size:12px;line-height:1.55}
input:focus,select:focus,textarea:focus{outline:none;border-color:%(edge)s}
select{width:150px}
.sw{position:relative;width:36px;height:19px;flex:none;background:%(ground)s;
  border:1px solid %(line)s;border-radius:10px;cursor:pointer}
.sw i{position:absolute;top:2px;left:2px;width:13px;height:13px;border-radius:50%%;
  background:%(dim)s;transition:left .14s,background .14s}
.sw.on{border-color:%(edge)s;background:%(edgesoft)s}
.sw.on i{left:19px;background:%(edge)s}
.sw:focus{outline:none;border-color:%(edge)s}
.note{font-size:11.5px;color:%(dim)s;line-height:1.65;margin:8px 0 4px}
.foot{flex:none;display:flex;align-items:center;gap:9px;padding:12px}
.foot .sp{flex:1}
button.act{font:inherit;font-size:12.5px;padding:7px 18px;background:%(card)s;
  color:%(ink)s;border:1px solid %(line)s;cursor:pointer}
button.act:hover{border-color:%(edge)s;color:%(edge)s}
button.pri{border-color:%(edge)s;color:%(edge)s}
button.act:disabled{opacity:.45;cursor:default}
/* penyedia AI */
.prow{display:flex;align-items:center;gap:8px;margin:10px 0}
.prow select{flex:1;width:auto}
#ptest{font-size:11.5px;color:%(dim)s;line-height:1.6;margin:8px 0 0;
  white-space:pre-wrap;max-height:120px;overflow:auto}
.key{display:flex;gap:8px;align-items:center}
.key input{flex:1;width:auto}
"""

PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>%(css)s</style></head>
<body>
<div class="tabs">%(tabbtns)s</div>
<div class="body">%(panes)s</div>
<div class="foot">
  <button class="act" id="guide">Cara dapat API key</button>
  <button class="act" id="raw">Config lanjutan</button>
  <span class="sp"></span>
  <button class="act" id="cancel">Batal</button>
  <button class="act pri" id="save">Simpan</button>
</div>
<script>
var PROV = %(providers)s;
var ACTIVE = %(active)s;

function tab(n){
  var bs = document.querySelectorAll(".tabs button");
  var ps = document.querySelectorAll(".pane");
  for (var i = 0; i < bs.length; i++){
    bs[i].classList.toggle("on", i === n);
    ps[i].classList.toggle("on", i === n);
  }
}
document.querySelectorAll(".tabs button").forEach(function(b, i){
  b.onclick = function(){ tab(i); };
});
tab(0);

// Saklar geser menggantikan kotak centang -- ini alasan utama formulir ini
// pindah ke halaman: kotak centang Qt yang diberi gaya kehilangan tanda
// centangnya, dan saklar tidak punya masalah itu sama sekali.
function bindSwitches(root){
  (root || document).querySelectorAll(".sw").forEach(function(s){
    if (s.dataset.bound) return;
    s.dataset.bound = "1";
    var flip = function(){
      s.classList.toggle("on");
      s.setAttribute("aria-checked", s.classList.contains("on") ? "true" : "false");
    };
    s.onclick = flip;
    s.onkeydown = function(e){
      if (e.key === " " || e.key === "Enter"){ e.preventDefault(); flip(); }
    };
  });
}
bindSwitches();

function collect(){
  var out = {};
  document.querySelectorAll("[data-k]").forEach(function(el){
    var k = el.dataset.k, t = el.dataset.t;
    if (t === "bool") out[k] = el.classList.contains("on");
    else if (t === "int") out[k] = parseInt(el.value, 10) || 0;
    else if (t === "float") out[k] = parseFloat(el.value) || 0;
    else out[k] = el.value;
  });
  return out;
}
</script>
%(provjs)s
<script>
document.getElementById("save").onclick = function(){
  pycmd("amdset:save:" + JSON.stringify(
    {fields: collect(), providers: PROV, active: activeName()}));
};
document.getElementById("cancel").onclick = function(){ pycmd("amdset:cancel:"); };
document.getElementById("guide").onclick  = function(){ pycmd("amdset:guide:"); };
document.getElementById("raw").onclick    = function(){ pycmd("amdset:raw:"); };
</script>
</body></html>"""


PROV_JS = """<script>
// Penyunting penyedia AI. Entri disunting DI TEMPAT, bukan dibangun ulang:
// tiap penyedia bisa memuat kolom yang formulir ini tidak pernah tampilkan --
// api_key_env, system_in_user, extra_headers -- dan menyusunnya ulang dari
// yang terlihat akan menghapus semuanya diam-diam.
(function(){
  var host = document.getElementById("prov");
  if (!host) return;
  var idx = Math.max(0, PROV.findIndex(function(p){ return p.name === ACTIVE; }));
  host.innerHTML =
    '<div class="prow"><select id="ppick"></select>' +
    '<button class="act" id="padd">+ Tambah</button>' +
    '<button class="act" id="pdel">Hapus</button></div>' +
    '<div class="r"><label for="pname">Nama</label>' +
      '<input id="pname" class="wide" type="text"></div>' +
    '<div class="r"><label for="pmodel">Model</label>' +
      '<input id="pmodel" class="wide" type="text"></div>' +
    '<div class="r"><label for="purl">Alamat API</label>' +
      '<input id="purl" class="wide" type="text"></div>' +
    '<div class="r"><label for="pwin">Jendela konteks (0 = ikut model)</label>' +
      '<input id="pwin" type="number" min="0" max="4000000" step="1000"></div>' +
    '<div class="r"><label for="pkey">API key</label>' +
      '<span class="key"><input id="pkey" type="password" class="wide">' +
      '<button class="act" id="pshow">Lihat</button>' +
      '<button class="act" id="ptestb">Tes koneksi</button></span></div>' +
    '<p id="ptest"></p>';

  var el = function(id){ return document.getElementById(id); };
  function refill(){
    var s = el("ppick"); s.innerHTML = "";
    PROV.forEach(function(p, i){
      var o = document.createElement("option");
      o.value = String(i); o.textContent = p.name || ("Provider " + (i + 1));
      s.appendChild(o);
    });
    s.value = String(idx);
  }
  function load(){
    var p = PROV[idx] || {};
    el("pname").value = p.name || "";
    el("pmodel").value = p.model || "";
    el("purl").value = p.base_url || "";
    el("pwin").value = p.context_window || 0;
    el("pkey").value = p.api_key || "";
    el("ptest").textContent = "";
  }
  function stash(){
    var p = PROV[idx];
    if (!p) return;
    p.name = el("pname").value.trim() || p.name || "Provider";
    p.model = el("pmodel").value.trim();
    p.base_url = el("purl").value.trim();
    p.api_key = el("pkey").value.trim();
    p.context_window = parseInt(el("pwin").value, 10) || 0;
    if (!p.kind) p.kind = "openai";
  }
  el("ppick").onchange = function(){ stash(); idx = +this.value; load(); refill(); };
  el("padd").onclick = function(){
    stash();
    PROV.push({name: "Baru", kind: "openai", model: "", base_url: "",
               api_key: "", context_window: 0});
    idx = PROV.length - 1; refill(); load();
  };
  el("pdel").onclick = function(){
    if (PROV.length <= 1){ el("ptest").textContent = "Sisa satu; tidak bisa dihapus."; return; }
    PROV.splice(idx, 1);
    idx = Math.min(idx, PROV.length - 1);
    refill(); load();
  };
  el("pshow").onclick = function(){
    var k = el("pkey");
    k.type = k.type === "password" ? "text" : "password";
    this.textContent = k.type === "password" ? "Lihat" : "Sembunyi";
  };
  el("ptestb").onclick = function(){
    stash();
    el("ptest").textContent = "Menghubungi…";
    pycmd("amdset:test:" + JSON.stringify(PROV[idx]));
  };
  window.amdTestResult = function(text){ el("ptest").textContent = text; };
  window.activeName = function(){ stash(); return (PROV[idx] || {}).name || ""; };
  refill(); load();
})();
</script>"""


def _build(raw):
    c = theme_mod.palette(theme_mod.name_of(raw))
    c = dict(c)
    c["edgesoft"] = theme_mod.rgba(c["edge"], 0.18)
    from .settings import TABS
    btns, panes = [], []
    for i, (name, fields) in enumerate(TABS):
        btns.append('<button%s>%s</button>' % (" class='on'" if i == 0 else "", _esc(name)))
        panes.append('<div class="pane%s">%s</div>'
                     % (" on" if i == 0 else "", _rows_html(fields, raw)))
    return PAGE % {
        "css": CSS % c,
        "tabbtns": "".join(btns),
        "panes": "\n".join(panes),
        "providers": json.dumps(raw.get("providers") or []),
        "active": json.dumps(raw.get("active_provider") or ""),
        "provjs": PROV_JS,
    }


class WebSettings(QDialog):
    """A dialog whose whole body is one page."""

    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.setWindowTitle("Amadeus Deck — Pengaturan")
        self.raw = mw.addonManager.getConfig(PACKAGE) or {}
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.web = AnkiWebView(self, title="amadeus settings")
        self.web.set_bridge_command(self._on_js, self)
        lay.addWidget(self.web)
        avail = self.screen().availableGeometry()
        self.resize(600, min(700, avail.height() - 120))
        self.setMaximumHeight(max(360, avail.height() - 60))
        self.web.stdHtml(_build(self.raw), css=[], js=[], context=self)

    # ---------------------------------------------------------------- bridge
    def _on_js(self, message):
        if not isinstance(message, str) or not message.startswith("amdset:"):
            return False
        _, verb, payload = message.split(":", 2)
        if verb == "cancel":
            self.reject()
        elif verb == "guide":
            from .settings import open_guide
            open_guide()
        elif verb == "raw":
            from .settings import open_raw
            self.reject()
            open_raw()
        elif verb == "save":
            self._save(payload)
        elif verb == "test":
            self._test(payload)
        return False

    def _save(self, payload):
        try:
            data = json.loads(payload)
        except ValueError:
            tooltip("Pengaturan tidak terbaca; tidak ada yang diubah.", period=4000)
            return
        fields = data.get("fields") or {}
        for key, value in fields.items():
            # Only keys the form actually owns. Anything else in the config --
            # the line pools, the mood tables -- is left exactly as it was.
            if key in self.raw or key in chatconf.DEFAULTS:
                self.raw[key] = value
        providers = data.get("providers")
        if isinstance(providers, list) and providers:
            self.raw["providers"] = providers
        active = data.get("active")
        if active:
            self.raw["active_provider"] = active
        mw.addonManager.writeConfig(PACKAGE, self.raw)
        # Menutup dulu, menggambar ulang belakangan. mw.reset() membongkar dan
        # membangun ulang webview Anki -- termasuk yang sedang menjalankan
        # jembatan ini. Memanggilnya dari dalam callback berarti merobohkan
        # lantai tempat kita berdiri, dan yang tersisa layar hitam.
        self.accept()
        mw.progress.single_shot(50, self._refresh, True)
        tooltip("Pengaturan disimpan.", period=3000)

    def _test(self, payload):
        try:
            entry = json.loads(payload)
        except ValueError:
            return
        from .settings import test_provider

        def report(text):
            # Datang dari utas latar; disampaikan ke halaman lewat utas utama.
            def show():
                if self.isVisible():
                    self.web.eval("window.amdTestResult && amdTestResult(%s)"
                                  % json.dumps(text))
            mw.taskman.run_on_main(show)

        test_provider(entry, report)

    def _refresh(self):
        """Gambar ulang semua permukaan yang memakai tema, tanpa restart."""
        try:
            from . import chat
            if chat.is_open():
                chat._dock._render()
        except Exception:
            pass
        try:
            mw.reset()
        except Exception:
            pass
        # Bilah atas dan bawah itu webview tersendiri; mw.reset() tidak
        # menyentuhnya, jadi warna temanya tertinggal sampai Anki dibuka ulang.
        for bar in ("toolbar", "bottomWeb"):
            try:
                widget = getattr(mw, bar, None)
                if widget is not None and hasattr(widget, "draw"):
                    widget.draw()
            except Exception:
                pass


def open_dialog():
    WebSettings(mw).exec()
