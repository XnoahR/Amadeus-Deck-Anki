"""The dialogue reveal: text typed one character at a time, with a blip per letter.

Both screens share this module so the deck panel and the reviewer overlay never
drift apart in feel.

The sound is synthesised rather than shipped as a file: it needs no asset routed
through the add-on's web exports, and it can be steered per character, which a
recording cannot.

Three things separate an 8-bit voice from a beep. The waveform is a 25% pulse,
not a plain square -- that thinner, reedier tone is the NES sound. The pitch
slides down slightly inside each syllable, which is what the ear reads as
speech. And the base pitch shifts with the letter being typed, so a sentence
has contour instead of one flat note repeated.
"""

DEFAULTS = {
    "typewriter": True,
    "typewriter_speed": 32,
    "dialog_sound": True,
    "dialog_volume": 0.16,
    "dialog_pitch": 440,
    "dialog_every": 3,
    "blink": True,
    "blink_min_ms": 2800,
    "blink_max_ms": 7000,
    "blink_hold_ms": 120,
    "dialog_mouth": True,
    "dialog_mouth_ms": 110,
    "dialog_caret": True,
    "dialog_caret_char": "\u258c",
}


def settings(c):
    """Config values clamped to what actually sounds and reads like dialogue."""
    def num(key, low, high):
        try:
            val = float(c.get(key, DEFAULTS[key]))
        except (TypeError, ValueError):
            val = DEFAULTS[key]
        return max(low, min(val, high))

    return {
        "on": bool(c.get("typewriter", DEFAULTS["typewriter"])),
        "speed": int(num("typewriter_speed", 5, 200)),
        "sound": bool(c.get("dialog_sound", DEFAULTS["dialog_sound"])),
        "vol": round(num("dialog_volume", 0.0, 1.0), 3),
        "pitch": round(num("dialog_pitch", 80, 2000)),
        "every": int(num("dialog_every", 1, 8)),
        "blink": bool(c.get("blink", DEFAULTS["blink"])),
        "blinkMin": int(num("blink_min_ms", 400, 60000)),
        "blinkMax": int(num("blink_max_ms", 600, 90000)),
        "blinkHold": int(num("blink_hold_ms", 40, 1000)),
        "mouth": bool(c.get("dialog_mouth", DEFAULTS["dialog_mouth"])),
        "mouthMs": int(num("dialog_mouth_ms", 40, 400)),
        "caret": bool(c.get("dialog_caret", DEFAULTS["dialog_caret"])),
        "caretChar": str(c.get("dialog_caret_char")
                         or DEFAULTS["dialog_caret_char"])[:2],
    }


JS = r"""
// The three pictures behind each expression are mouth positions -- shut, ajar,
// open -- not variations on a pose. Walking them 1-2-3-2-1 is a mouth moving;
// picking one at random, which is what everything here did before, leaves her
// resting mid-word with her mouth hanging open.
function amdMouth(apply, framesOf, ms, blink){
  var timer = null, frames = [], i = 0, dir = 1, mood = null;
  var blinker = null, holding = null, talking = false;

  function rest(){
    frames = framesOf(mood) || [];
    if (frames.length) apply(frames[0]);
  }

  // Which closed-eye set matches the pose she is holding. The add-on already
  // groups pictures by the mood their filename ends with, so reading "sided"
  // off the current frame is the same convention, not a new assumption.
  function shut(){
    if (!blink || !blink.on) return null;
    var sided = frames.length && /sided/.test(frames[0]);
    var set = (sided && blink.sided && blink.sided.length) ? blink.sided : blink.closed;
    return (set && set.length) ? set[0] : null;
  }

  function laterBlink(){
    if (!blink || !blink.on) return;
    var lo = blink.min || 2800, hi = blink.max || 7000;
    clearTimeout(blinker);
    blinker = setTimeout(doBlink, lo + Math.random() * Math.max(1, hi - lo));
  }

  function doBlink(){
    // Never over a line being spoken: the mouth is mid-cycle and an eyes-shut
    // frame would fight it for the same img.
    var src = talking ? null : shut();
    if (!src) { laterBlink(); return; }
    apply(src);
    clearTimeout(holding);
    holding = setTimeout(function(){
      if (!talking) rest();
      // Blinks come in pairs often enough that always singles reads as a tic.
      if (Math.random() < 0.25 && !talking){
        clearTimeout(holding);
        holding = setTimeout(function(){
          var again = talking ? null : shut();
          if (again){
            apply(again);
            setTimeout(function(){ if (!talking) rest(); }, blink.hold || 120);
          }
        }, 170);
      }
      laterBlink();
    }, blink.hold || 120);
  }

  return {
    // Called whenever the expression changes, not only while she is speaking.
    set: function(name){ mood = name; if (!timer) rest(); },
    start: function(){
      talking = true;
      frames = framesOf(mood) || [];
      if (frames.length < 2) return;
      if (timer) clearInterval(timer);
      i = 0; dir = 1;
      timer = setInterval(function(){
        if (i + dir > frames.length - 1) dir = -1;
        else if (i + dir < 0) dir = 1;
        i += dir;
        apply(frames[i]);
      }, ms || 110);
    },
    stop: function(){
      talking = false;
      if (timer) { clearInterval(timer); timer = null; }
      if (frames.length) apply(frames[0]);   // shut, always
    },
    // Started by the caller once the pictures are known, so a character with no
    // eyes_closed set simply never blinks instead of blinking to a wrong face.
    blink: function(){
      var still = window.matchMedia &&
                  window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (still) return;
      laterBlink();
    }
  };
}

function amdVoice(o, hooks){
  o = o || {}; hooks = hooks || {};
  var AC = null, wave = null, tick = null;
  var full = "", node = null, n = 0, streaming = false;
  var body = null, caret = null, blinker = null;

  // A 25% duty pulse, built from its Fourier series. Web Audio only ships a
  // 50% square, which is the fat tone; the NES's thin one is this.
  function pulse(ac){
    var H = 22, real = new Float32Array(H), imag = new Float32Array(H);
    for (var i = 1; i < H; i++) real[i] = (2 / (i * Math.PI)) * Math.sin(Math.PI * i * 0.25);
    return ac.createPeriodicWave(real, imag);
  }

  function ctx(){
    var C = window.AudioContext || window.webkitAudioContext;
    if (!C) return null;
    if (!AC) { AC = new C(); wave = pulse(AC); }
    return AC;
  }

  function blip(ch){
    if (!o.sound || !o.vol) return;
    try {
      if (!ctx()) return;
      // Created suspended until the page has been interacted with. Ask once and
      // stay quiet rather than throwing on every letter.
      if (AC.state === "suspended") { AC.resume(); return; }
      var t = AC.currentTime;
      // Letter picks the note, so a sentence has contour rather than one flat
      // tone repeated at you.
      var step = ch.charCodeAt(0) % 5;
      var base = o.pitch * (0.88 + step * 0.06);
      var osc = AC.createOscillator(), g = AC.createGain();
      osc.setPeriodicWave(wave);
      osc.frequency.setValueAtTime(base, t);
      // The slide is the part that reads as talking instead of beeping.
      osc.frequency.exponentialRampToValueAtTime(base * 0.8, t + 0.05);
      g.gain.setValueAtTime(0.0001, t);
      g.gain.linearRampToValueAtTime(o.vol, t + 0.004);   // short, but not
      g.gain.setValueAtTime(o.vol, t + 0.032);            // instant: a hard
      g.gain.linearRampToValueAtTime(0.0001, t + 0.052);  // gate clicks
      osc.connect(g); g.connect(AC.destination);
      osc.start(t); osc.stop(t + 0.06);
    } catch (e) {}
  }

  function unmount(){
    if (blinker) { clearInterval(blinker); blinker = null; }
    if (caret && caret.parentNode) caret.parentNode.removeChild(caret);
    caret = null;
  }

  function fire(name){
    if (typeof hooks[name] === "function") { try { hooks[name](); } catch (e) {} }
  }

  function stop(){
    var was = !!tick;
    if (tick) { clearInterval(tick); tick = null; }
    unmount();
    if (was) fire("stop");
  }

  // A text node plus a caret element, rather than writing textContent, because
  // textContent would wipe the caret on every character.
  function mount(el){
    el.textContent = "";
    body = document.createTextNode("");
    el.appendChild(body);
    if (!o.caret) return;
    caret = document.createElement("span");
    caret.textContent = o.caretChar || "\u258c";
    // Blinked from JS rather than a CSS keyframe: the reviewer overlay lives in
    // a shadow root, where a stylesheet added to the document never reaches it.
    caret.style.opacity = "1";
    var on = true;
    blinker = setInterval(function(){
      on = !on;
      caret.style.opacity = on ? "1" : "0";
    }, 530);
    el.appendChild(caret);
  }

  // One cursor walking one buffer. say() fills the buffer in one go; a streamed
  // reply grows it while the cursor is still walking, which is why the typing
  // rhythm survives a model that arrives in bursts.
  function step(){
    if (n >= full.length) { if (!streaming) stop(); return; }
    var ch = full.charAt(n++);
    body.nodeValue = full.slice(0, n);
    var every = o.every || 3;
    // Not on every letter, and never on a pause: one syllable per character is
    // a buzz, and punctuation is where a voice would stop anyway.
    if (n % every === 0 && ch.trim() &&
        "、。，．！？…!?,.:;「」『』\"'".indexOf(ch) < 0) blip(ch);
  }

  function begin(el){
    stop();
    node = el; n = 0;
    mount(el);
    tick = setInterval(step, o.speed);
    fire("start");
  }

  return {
    say: function(el, text){
      stop();
      node = el; full = (text == null) ? "" : String(text); streaming = false;
      if (!o.on || !full) { el.textContent = full; return; }
      begin(el);
    },
    // A reply that is still being generated: open the line, push what arrives,
    // close it when the model stops. The caret keeps blinking through the gaps,
    // which is the honest signal that more is coming.
    open: function(el){
      full = ""; streaming = true;
      if (!o.on) { el.textContent = ""; node = el; return; }
      begin(el);
    },
    push: function(text){
      full += (text == null) ? "" : String(text);
      if (!o.on && node) node.textContent = full;
    },
    close: function(){
      streaming = false;
      if (!tick && node) { node.textContent = full; unmount(); }
    },
    text: function(){ return full; },
    // Clicking mid-line finishes it, the way every visual novel does, instead of
    // throwing the sentence away for a new one nobody asked for. Mid-stream it
    // catches up to whatever has arrived and keeps going.
    skip: function(){
      if (!tick) return false;
      if (body) body.nodeValue = full;
      else if (node) node.textContent = full;
      n = full.length;
      if (!streaming) stop();
      return true;
    },
    // Call from inside a real click handler: resuming from a timer tick is not
    // reliably counted as the interaction the browser is waiting for.
    wake: function(){
      if (!o.sound) return;
      try { if (ctx() && AC.state === "suspended") AC.resume(); } catch (e) {}
    }
  };
}
"""
