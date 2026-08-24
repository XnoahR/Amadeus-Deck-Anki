# SPDX-License-Identifier: MIT
"""Film grain, in one place for the three screens that want it.

Written once because it was wrong in three different ways at once: the deck
panel had a noise layer that was never given an image, so the effect had simply
never existed there; the reviewer and the chat both composited an opaque tile
with mix-blend-mode: overlay, which leaves a near-black backdrop untouched --
measured across a flat area, a standard deviation of 1 in 255.

Random alpha with no blend mode reads the same on a black ground and on paper,
because it does not consult the ground at all. And four tiles swapped in turn
beat one tile slid around by a keyframe: sliding is a moving pattern, and the
eye names it as one immediately.
"""

from typing import Any

DEFAULT_OPACITY = 0.45
TILE = 96          # 64 starts reading as a repeating motif at any useful strength
ALPHA = 120
FRAMES = 4
INTERVAL = 90      # ms


def settings(cfg: dict[str, Any]) -> dict[str, Any]:
    try:
        opacity = float(cfg.get("grain_opacity", DEFAULT_OPACITY))
    except (TypeError, ValueError):
        opacity = DEFAULT_OPACITY
    return {
        "on": bool(cfg.get("effects", True)) and opacity > 0,
        "opacity": round(max(0.0, min(opacity, 1.0)), 3),
        "size": TILE, "alpha": ALPHA, "frames": FRAMES, "ms": INTERVAL,
    }


JS = r"""
function amdGrain(el, o){
  if (!el || !o || !o.on) return;
  el.style.opacity = o.opacity;
  el.style.backgroundRepeat = "repeat";
  var tiles = [];
  for (var t = 0; t < o.frames; t++){
    var cv = document.createElement("canvas");
    cv.width = cv.height = o.size;
    var cx = cv.getContext("2d"), id = cx.createImageData(o.size, o.size);
    for (var i = 0; i < id.data.length; i += 4){
      var v = (Math.random() * 255) | 0;
      id.data[i] = id.data[i+1] = id.data[i+2] = v;
      id.data[i+3] = o.alpha;
    }
    cx.putImageData(id, 0, 0);
    tiles.push("url(" + cv.toDataURL("image/png") + ")");
  }
  el.style.backgroundImage = tiles[0];
  var still = window.matchMedia &&
              window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (still || tiles.length < 2) return;
  var k = 0;
  setInterval(function(){
    // never the same tile twice running, or it reads as a stutter rather than
    // as grain
    k = (k + 1 + ((Math.random() * (tiles.length - 1)) | 0)) % tiles.length;
    el.style.backgroundImage = tiles[k];
  }, o.ms);
}
"""
