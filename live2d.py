"""A Live2D model in the chat face, when the user has one.

Nothing here ships. The Cubism runtime belongs to Live2D Inc. and a model
belongs to whoever drew it, so both stay out of the repository -- exactly like
the character art. The add-on looks in `user_files/live2d/` and uses what it
finds; an empty folder simply means the pictures keep their job.

Falling back matters more than the feature. WebGL is off on some machines, a
model can fail to parse, a runtime file can be half-downloaded. Every one of
those has to end with the PNG face still on screen, so the canvas is only shown
after a model has actually rendered a frame.
"""
import os

FOLDER = "live2d"
LIBS = ("live2d.min.js", "pixi.min.js", "cubism2.min.js")


def folder(addon_dir):
    return os.path.join(addon_dir, "user_files", FOLDER)


def _model_json(root):
    """The first model definition, preferring one that names itself."""
    try:
        names = sorted(os.listdir(root))
    except OSError:
        return None
    liked = [n for n in names if n.endswith(".model.json")]
    liked += [n for n in names if n.endswith(".json") and n not in liked
              and n not in ("index.json",)]
    for n in liked:
        return n
    return None


def state(addon, addon_dir):
    """What the page needs to decide whether it can even try."""
    root = folder(addon_dir)
    lib = os.path.join(root, "lib")
    have = [n for n in LIBS if os.path.isfile(os.path.join(lib, n))]
    model = _model_json(root)
    base = "/_addons/%s/user_files/%s/" % (addon, FOLDER)
    return {
        "ready": len(have) == len(LIBS) and bool(model),
        "libs": [base + "lib/" + n for n in LIBS if n in have],
        "missing": [n for n in LIBS if n not in have] + ([] if model else ["model .json"]),
        "model": (base + model) if model else "",
    }


def settings(cfg):
    def num(key, default, lo, hi):
        try:
            v = float(cfg.get(key, default))
        except (TypeError, ValueError):
            v = default
        return max(lo, min(hi, v))
    return {
        "on": bool(cfg.get("live2d", False)),
        "fade": int(num("live2d_fade_ms", 260, 0, 1500)),
        "mouth": bool(cfg.get("live2d_lipsync", True)),
        "gain": num("live2d_mouth_gain", 1.6, 0.2, 6.0),
        "head": bool(cfg.get("live2d_head_tilt", True)),
        # Seberapa tinggi sosoknya dibanding tinggi panel. 1,0 berarti dari
        # ubun-ubun sampai tepi bawah; di bawah itu ia mundur menjauh.
        # 1,12 menyamai gambar PNG-nya persis: height 112%, bertumpu di bawah.
        "zoom": num("live2d_zoom", 1.12, 0.4, 3.0),
        # Geser tegak, dalam pecahan tinggi panel. Negatif menaikkan.
        "offy": num("live2d_offset_y", 0.0, -1.0, 1.0),
        # Berapa lama sebuah ekspresi bertahan sebelum mengendur kembali ke
        # wajah diam. 0 mematikannya -- ekspresi terakhir bertahan selamanya.
        "idle": int(num("live2d_idle_ms", 5000, 0, 60000)),
    }


# Expressions are built from the axes that actually move this rig. Measured on
# the Kurisu model with a zero noise floor: eye openness carries the most, then
# gaze, then brows; mouth form barely registers but mouth opening does.
# EYE_SMILE, TERE and DONYORI move nothing at all and are deliberately absent.
FACES = {
    "normal":    {"EO": 1.0,  "BY": 0.0,  "EX": 0,    "EY": 0,    "MF": 0},
    "happy":     {"EO": 0.55, "BY": 0.6,  "EX": 0,    "EY": 0,    "MF": 1},
    "thinking":  {"EO": 0.65, "BY": -0.3, "EX": -0.8, "EY": 0.8,  "MF": -0.2},
    "sad":       {"EO": 0.5,  "BY": 0.75, "EX": 0,    "EY": -0.7, "MF": -0.9},
    "annoyed":   {"EO": 0.42, "BY": -1.0, "EX": 0,    "EY": -0.4, "MF": -1},
    "blush":     {"EO": 0.6,  "BY": 0.5,  "EX": -0.9, "EY": 0,    "MF": -0.5},
    "surprised": {"EO": 1.0,  "BY": 1.0,  "EX": 0,    "EY": 0.2,  "MF": 0},
}

# Gerak kepala per suasana, angkanya dari mockup. Tiap titik: [detik, X, Y, Z].
# Dua titik dengan nilai sama berarti berhenti sejenak -- itu yang membedakan
# "berpikir" dari "kepala goyang".
GESTURES = {
    "happy":     [[0, 0, 0, 0], [0.18, 0, -13, 2], [0.36, 0, 4, 0],
                  [0.54, 0, -10, 1], [0.78, 0, 0, 0]],
    "annoyed":   [[0, 0, 0, 0], [0.16, -17, -5, 5], [0.34, 16, -6, -5],
                  [0.52, -12, -6, 4], [0.70, 9, -5, -3], [0.90, -4, -4, 1],
                  [1.40, 0, 0, 0]],
    "thinking":  [[0, 0, 0, 0], [0.5, -8, 14, -6], [1.9, -9, 15, -7],
                  [2.6, 0, 0, 0]],
    "surprised": [[0, 0, 0, 0], [0.09, 4, -14, -9], [0.26, -3, -8, 6],
                  [0.44, 2, -4, -3], [0.95, 0, 0, 0]],
    "sad":       [[0, 0, 0, 0], [0.7, 0, -12, 4], [1.6, 0, -13, 5],
                  [2.4, 0, 0, 0]],
    "blush":     [[0, 0, 0, 0], [0.3, 18, 8, -9], [1.3, 19, 9, -10],
                  [2.0, 0, 0, 0]],
}

# A few degrees only. More than this and it stops reading as a face and starts
# reading as the whole picture being shoved around.
TILT = {
    "normal": (0, 0, 0), "happy": (0, 2, 3), "thinking": (-3, 4, -3),
    "sad": (0, -5, 2), "annoyed": (0, -2, 2), "blush": (5, 0, 3),
    "surprised": (0, -4, -2),
}


JS = r"""
// amdLive2D(host, cfg, faces, tilt) -> {ready, mood, mouth, stop}
// Draws into a canvas laid over the PNG face. The canvas stays hidden until a
// frame has actually been rendered, so every failure path leaves the picture.
function amdLive2D(host, cfg, FACES, TILT, GEST, done){
  GEST = GEST || {};
  var api = {ready:false, mood:function(){}, mouth:function(){},
             talk:function(){}, voiced:function(){}, stop:function(){}};
  if (!cfg || !cfg.on || !cfg.ready) return api;

  var cv = document.createElement("canvas");
  // Ukuran kanvas mengikuti bentuk panelnya, bukan angka tetap. Kanvas 500x600
  // yang diregangkan ke panel 420x220 membuat wajahnya melebar -- itu bukan
  // modelnya yang salah, itu piksel yang ditarik paksa.
  var wide = Math.max(120, host.clientWidth || 420);
  var tall = Math.max(90, host.clientHeight || 220);
  var dpr = Math.min(2, window.devicePixelRatio || 1);
  cv.width = Math.round(wide * dpr);
  cv.height = Math.round(tall * dpr);
  cv.style.cssText = "position:absolute;left:0;top:0;width:100%;height:100%;" +
                     "opacity:0;transition:opacity 320ms;z-index:2;pointer-events:none";
  host.appendChild(cv);

  function load(list, then){
    if (!list.length) return then();
    var s = document.createElement("script");
    s.src = list[0];
    s.onload = function(){ load(list.slice(1), then); };
    s.onerror = function(){ then(new Error("gagal memuat " + list[0])); };
    document.head.appendChild(s);
  }

  load(cfg.libs.slice(), function(err){
    if (err || !window.PIXI || !window.PIXI.live2d || !window.Live2D) return;
    if (!document.createElement("canvas").getContext("webgl")) return;
    var app;
    try {
      app = new PIXI.Application({view:cv, backgroundAlpha:0,
                                  width:cv.width, height:cv.height,
                                  antialias:true, preserveDrawingBuffer:true});
    } catch (e) { return; }

    PIXI.live2d.Live2DModel.from(cfg.model, {autoInteract:false}).then(function(model){
      app.stage.addChild(model);
      var W = cv.width, H = cv.height;   // diperbarui saat panel berubah
      var ow = model.internalModel.originalWidth || 1920;
      var oh = model.internalModel.originalHeight || 1980;
      model.anchor.set(.5, .5);

      // Framing is measured, never assumed: the model's own bounds are far
      // larger than what is drawn, and its canvas centre is not her centre.
      var p2 = document.createElement("canvas"); p2.width = W; p2.height = H;
      var pg = p2.getContext("2d", {willReadFrequently:true});
      function box(){
        pg.clearRect(0,0,W,H);
        try { pg.drawImage(cv,0,0,W,H); } catch (e) { return null; }
        var d = pg.getImageData(0,0,W,H).data, x0=W,y0=H,x1=-1,y1=-1;
        for (var y=0;y<H;y++) for (var x=0;x<W;x++)
          if (d[(y*W+x)*4+3] > 24){ if(x<x0)x0=x; if(x>x1)x1=x;
                                    if(y<y0)y0=y; if(y>y1)y1=y; }
        return x1 < 0 ? null : {x:x0,y:y0,w:x1-x0+1,h:y1-y0+1};
      }
      function fit(){
        var s0 = Math.min(W/ow, H/oh) * 0.9;
        model.scale.set(s0); model.position.set(W/2, H/2); app.render();
        var v = box(); if (!v) return false;
        // Head-and-shoulders: the face fills the frame rather than the bust,
        // because at this size a full bust leaves the face unreadable.
        var dx = (v.x + v.w/2 - model.x) / s0, dy = (v.y - model.y) / s0;
        var s1 = s0 * ((H * (cfg.zoom || 1.12)) / v.h);
        // Bertumpu di tepi bawah, persis seperti gambar PNG-nya
        // (bottom:0; height:112%). Jadi zoom 1.12 memberi bingkai yang sama,
        // dan geser 0 berarti sejajar -- bukan melayang di tengah.
        var top = H - H * (cfg.zoom || 1.12) + H * (cfg.offy || 0);
        model.scale.set(s1); model.position.set(W/2 - dx*s1, top - dy*s1);
        app.render(); return true;
      }
      // Gerak diam bawaannya dibiarkan hidup: napas, kedip, ayunan rambut.
      try { model.motion("idle"); } catch (e) {}
      // Panel chat bisa diubah lebarnya kapan saja. Kanvas yang ukurannya
      // dikunci sekali saat dibuat akan diregangkan CSS -- melebar persis
      // seperti sebelumnya, hanya dengan sebab yang berbeda. Jadi ukurannya
      // dihitung ulang tiap panelnya berubah, lalu dibingkai ulang.
      var resizing = null;
      function resize(){
        var w2 = Math.max(120, host.clientWidth || wide);
        var h2 = Math.max(90, host.clientHeight || tall);
        var nw = Math.round(w2 * dpr), nh = Math.round(h2 * dpr);
        if (nw === cv.width && nh === cv.height) return;
        try { app.renderer.resize(nw, nh); } catch (e) { return; }
        cv.width = nw; cv.height = nh;
        W = nw; H = nh;
        p2.width = nw; p2.height = nh;
        fit();
      }
      if (window.ResizeObserver){
        new ResizeObserver(function(){
          clearTimeout(resizing);
          // Menunggu sebentar: menggeser tepi jendela memicu puluhan kejadian,
          // dan membingkai ulang tiap kali berarti mengukur piksel puluhan kali.
          resizing = setTimeout(resize, 120);
        }).observe(host);
      } else {
        window.addEventListener("resize", function(){
          clearTimeout(resizing); resizing = setTimeout(resize, 120);
        });
      }

      var tries = 0;
      (function settle(){
        if (fit() || ++tries > 40){
          cv.style.opacity = "1";
          api.ready = true;
          // Dua Amadeus sekaligus kalau yang lama tidak disingkirkan. Baru
          // sekarang, setelah ada bingkai sungguhan -- kalau langkah mana pun
          // di atas gagal, gambarnya tidak pernah hilang.
          var img = host.querySelector("img");
          if (img){ img.dataset.amdHidden = "1"; img.style.visibility = "hidden"; }
          if (done) done(true);
          return;
        }
        requestAnimationFrame(settle);
      })();

      var core = model.internalModel.coreModel;
      var MAP = {EO:["PARAM_EYE_L_OPEN","PARAM_EYE_R_OPEN"],
                 BY:["PARAM_BROW_L_Y","PARAM_BROW_R_Y"],
                 EX:["PARAM_EYE_BALL_X"], EY:["PARAM_EYE_BALL_Y"],
                 MF:["PARAM_MOUTH_FORM"]};
      var now = {EO:1,BY:0,EX:0,EY:0,MF:0}, from = {}, to = {EO:1,BY:0,EX:0,EY:0,MF:0};
      var nowT = {X:0,Y:0,Z:0}, fromT = {}, toT = {X:0,Y:0,Z:0};
      var t0 = 0, open = 0, gest = null, gt0 = 0, relax = null;

      model.internalModel.on("beforeModelUpdate", function(){
        for (var k in MAP) for (var i=0;i<MAP[k].length;i++)
          core.setParamFloat(MAP[k][i], now[k]);
        core.setParamFloat("PARAM_MOUTH_OPEN_Y", open);
        if (cfg.head){
          // Ditambahkan, bukan ditimpakan. Kalau ditimpakan, gerak diam
          // bawaannya -- napas, ayunan kepala pelan -- mati dan dia jadi patung
          // yang cuma berkedip.
          var gx = 0, gy = 0, gz = 0;
          if (gest){
            var t = (performance.now() - gt0) / 1000;
            var k = gest;
            if (t >= k[k.length-1][0]) gest = null;
            else {
              var a = k[0], b = k[k.length-1];
              for (var i = 0; i < k.length-1; i++)
                if (t >= k[i][0] && t < k[i+1][0]){ a = k[i]; b = k[i+1]; break; }
              var sp = Math.max(0.0001, b[0] - a[0]);
              var u = (t - a[0]) / sp;
              u = u < 0.5 ? 2*u*u : 1 - Math.pow(-2*u+2, 2)/2;
              gx = a[1] + (b[1]-a[1])*u; gy = a[2] + (b[2]-a[2])*u;
              gz = a[3] + (b[3]-a[3])*u;
            }
          }
          core.setParamFloat("PARAM_ANGLE_X",
            core.getParamFloat("PARAM_ANGLE_X") + nowT.X + gx);
          core.setParamFloat("PARAM_ANGLE_Y",
            core.getParamFloat("PARAM_ANGLE_Y") + nowT.Y + gy);
          core.setParamFloat("PARAM_ANGLE_Z",
            core.getParamFloat("PARAM_ANGLE_Z") + nowT.Z + gz);
        }
      });

      app.ticker.add(function(){
        var ms = cfg.fade || 0;
        if (ms <= 0){ for (var q in to) now[q] = to[q];
                      for (var r in toT) nowT[r] = toT[r]; return; }
        var u = Math.min(1, (performance.now() - t0) / ms);
        var w = u < 0.5 ? 2*u*u : 1 - Math.pow(-2*u+2, 2)/2;
        for (var k in to){
          var a = from[k] == null ? to[k] : from[k];
          now[k] = a + (to[k] - a) * w;
        }
        for (var k2 in toT){
          var b = fromT[k2] == null ? toT[k2] : fromT[k2];
          nowT[k2] = b + (toT[k2] - b) * w;
        }
      }, null, PIXI.UPDATE_PRIORITY.NORMAL);

      api.mood = function(name){
        var f = FACES[name] || FACES.normal;
        var t = TILT[name] || TILT.normal || [0,0,0];
        for (var k in now) from[k] = now[k];
        for (var k2 in nowT) fromT[k2] = nowT[k2];
        for (var k3 in f) to[k3] = f[k3];
        toT.X = t[0]; toT.Y = t[1]; toT.Z = t[2];
        t0 = performance.now();
        var g = GEST[name];
        if (g && cfg.head){ gest = g; gt0 = performance.now(); }
        // Sebuah ekspresi adalah reaksi, bukan keadaan tetap. Tanpa ini
        // wajahnya berhenti di mood terakhir dan tidak pernah kembali tenang.
        clearTimeout(relax);
        if (cfg.idle > 0 && name !== "normal"){
          relax = setTimeout(function(){ api.mood("normal"); }, cfg.idle);
        }
      };
      api.mouth = function(v){ open = Math.max(0, Math.min(2, v)); };
      // Ketika tidak ada rekaman yang berbunyi, mulutnya mengikuti ketikan --
      // bukan diam. Amplitudonya diacak sedikit supaya tidak terdengar seperti
      // metronom, dan berhenti rapat begitu kalimatnya selesai.
      // Dua sumber mulut yang tidak boleh saling menimpa: rekaman menang
      // selama ia berbunyi, ketikan mengambil alih sesudahnya. Tanpa aturan
      // ini keduanya saling menyalakan dan mulutnya membuka-tutup selamanya.
      var chat = null, typing = false, voiced = false;
      function chew(){
        if (chat) return;
        var t = 0;
        chat = setInterval(function(){
          t += 1;
          open = Math.max(0, Math.sin(t * 0.9)) * (0.5 + Math.random() * 0.5) * 1.5;
        }, 90);
      }
      function still(){ if (chat){ clearInterval(chat); chat = null; } open = 0; }
      api.talk = function(on){ typing = !!on; if (typing && !voiced) chew(); else still(); };
      api.voiced = function(level){
        if (level > 0){ voiced = true; still(); open = Math.max(0, Math.min(2, level)); }
        else if (voiced){ voiced = false; if (typing) chew(); else still(); }
      };
      api.stop = function(){
        try { app.destroy(); } catch (e) {}
        cv.remove();
        var img = host.querySelector("img[data-amd-hidden]");
        if (img){ img.style.visibility = ""; delete img.dataset.amdHidden; }
      };
    }).catch(function(){ /* model tidak terbaca: gambar PNG tetap di tempatnya */ });
  });

  return api;
}

// amdSpeak(cfg, onLevel) -> {play(url), quiet()}
// Plays a clip and reports its loudness each frame, so the mouth follows the
// voice instead of the letters. Falls back to a plain <audio> when the Web
// Audio graph cannot be built -- then there is no level, only sound.
function amdSpeak(cfg, onLevel){
  var AC = window.AudioContext || window.webkitAudioContext;
  var ctx = null, node = null, an = null, buf = null, raf = null, el = null;

  function stopLoop(){ if (raf) cancelAnimationFrame(raf); raf = null; }

  function loop(){
    if (!an) return;
    an.getByteTimeDomainData(buf);
    var sum = 0;
    for (var i = 0; i < buf.length; i++){ var d = (buf[i] - 128) / 128; sum += d*d; }
    var rms = Math.sqrt(sum / buf.length);
    onLevel(Math.min(2, rms * (cfg.gain || 1.6) * 6));
    raf = requestAnimationFrame(loop);
  }

  return {
    play: function(url){
      try { if (el){ el.pause(); } } catch (e) {}
      stopLoop();
      el = new Audio(url);
      el.crossOrigin = "anonymous";
      el.volume = cfg.vol == null ? 0.9 : cfg.vol;
      if (cfg.mouth && AC){
        try {
          if (!ctx) ctx = new AC();
          if (ctx.state === "suspended") ctx.resume();
          node = ctx.createMediaElementSource(el);
          an = ctx.createAnalyser(); an.fftSize = 512;
          buf = new Uint8Array(an.fftSize);
          node.connect(an); an.connect(ctx.destination);
          raf = requestAnimationFrame(loop);
        } catch (e) { an = null; }
      }
      el.onended = function(){ stopLoop(); onLevel(0); };
      var p = el.play();
      if (p && p.catch) p.catch(function(){ stopLoop(); onLevel(0); });
      return true;
    },
    // Dipanggil pada sentuhan pertama: cukup buka AudioContext-nya, tanpa
    // memutar apa pun.
    wake: function(){
      try {
        if (!ctx && AC) ctx = new AC();
        if (ctx && ctx.state === "suspended") ctx.resume();
      } catch (e) {}
    },
    quiet: function(){ try { if (el) el.pause(); } catch (e) {} stopLoop(); onLevel(0); }
  };
}
"""
