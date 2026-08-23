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
    }


JS = r"""
function amdVoice(o){
  o = o || {};
  var AC = null, wave = null, tick = null, full = "", node = null, n = 0;

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

  function stop(){ if (tick) { clearInterval(tick); tick = null; } }

  return {
    say: function(el, text){
      stop();
      node = el; full = (text == null) ? "" : String(text);
      if (!o.on || !full) { el.textContent = full; return; }
      el.textContent = ""; n = 0;
      var every = o.every || 3;
      tick = setInterval(function(){
        if (n >= full.length) { stop(); return; }
        var ch = full.charAt(n++);
        el.textContent += ch;
        // Not on every letter, and never on a pause: one syllable per character
        // is a buzz, and punctuation is where a voice would stop anyway.
        if (n % every === 0 && ch.trim() &&
            "、。，．！？…!?,.:;「」『』\"'".indexOf(ch) < 0) blip(ch);
      }, o.speed);
    },
    // Clicking mid-line finishes it, the way every visual novel does, instead of
    // throwing the sentence away for a new one nobody asked for.
    skip: function(){
      if (!tick) return false;
      stop();
      if (node) node.textContent = full;
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
