"""The frame draws a new expression instead of cutting to it.

Two separate things live here, and each has its own switch.

The first is how an expression arrives. Swapping the picture in one frame is
correct and reads like nothing at all: she is simply someone else now. So the
frame is emptied first -- for a moment there is nothing behind the glass but
the raster -- and the new picture is built downwards behind a scan head. The
step count is deliberately low; a smooth reveal looks like a fade, a coarse one
looks like a machine drawing lines.

The second is the tracking fault: every so often one horizontal band slips
sideways and brightens, the way a tape does when the head is not quite tracking.
It is a copy of the same picture clipped to a band and nudged with `left`, never
`transform` -- the pictures are centred with `translateX(-50%)` and writing over
that would throw them off-centre.

Nothing here touches the mouth or the blink. Those swap pictures every 90-110ms;
any sweep is slower than that, so a sweep on every frame would leave her mouth
permanently mid-draw. Only a change of expression sweeps.
"""

DEFAULTS = {
    "frame_scan": False,
    "frame_scan_ms": 320,
    "frame_scan_steps": 4,
    "frame_scan_line": 2,
    "tracking": False,
    "tracking_strength": 7,
}


def settings(cfg):
    """What the pages need, already in JS shapes."""
    def num(key, lo, hi):
        try:
            v = int(cfg.get(key, DEFAULTS[key]))
        except (TypeError, ValueError):
            v = DEFAULTS[key]
        return max(lo, min(hi, v))

    return {
        "scan": bool(cfg.get("frame_scan", DEFAULTS["frame_scan"])),
        "ms": num("frame_scan_ms", 80, 2000),
        "steps": num("frame_scan_steps", 2, 40),
        "line": num("frame_scan_line", 0, 12),
        "track": bool(cfg.get("tracking", DEFAULTS["tracking"])),
        "amp": num("tracking_strength", 1, 30),
    }


JS = r"""
// amdWarp(host, imgs, opts) -> {swap, set}
//   set(src)  puts the picture up with no ceremony -- mouth frames, blinks
//   swap(src) draws it in, if that is switched on
function amdWarp(host, imgs, o){
  o = o || {};
  var list = [].slice.call(imgs || []);
  function set(src){ for (var i = 0; i < list.length; i++) list[i].src = src; }
  if (!list.length || !host) return {swap: set, set: set};

  var still = window.matchMedia &&
              window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (still || (!o.scan && !o.track)) return {swap: set, set: set};

  if (getComputedStyle(host).position === "static") host.style.position = "relative";

  if (!document.getElementById("amd-warp-css")){
    var st = document.createElement("style");
    st.id = "amd-warp-css";
    st.textContent =
      ".amd-tear{opacity:0}" +
      ".amd-raster,.amd-head{position:absolute;pointer-events:none;opacity:0}" +
      ".amd-raster{inset:0;transition:opacity 80ms;background:repeating-linear-gradient(" +
        "180deg,rgba(255,255,255,.10) 0 1px,rgba(0,0,0,.55) 1px 3px)}" +
      ".amd-head{left:0;right:0;top:0;background:linear-gradient(90deg," +
        "transparent,rgba(255,255,255,.85),transparent)}";
    document.head.appendChild(st);
  }

  // The extra picture goes in among the pictures, so the scan lines and the
  // grain still lie over it. The two overlays go last, over everything.
  var tear = null;
  if (o.track){
    tear = list[0].cloneNode(false);
    tear.removeAttribute("id");
    tear.className = (tear.className ? tear.className + " " : "") + "amd-tear";
    tear.src = list[0].getAttribute("src") || "";
    var after = list[list.length - 1];
    if (after.parentNode) after.parentNode.insertBefore(tear, after.nextSibling);
    else host.appendChild(tear);
  }
  // Everything that puts a picture up goes through here, so the tracking
  // copy never shows a frame older than the face behind it -- her mouth moves
  // every 110ms and a stale band would lag a whole word behind.
  function put(src){ set(src); if (tear) tear.src = src; }

  var raster = null, head = null;
  if (o.scan){
    raster = document.createElement("div");
    raster.className = "amd-raster";
    host.appendChild(raster);
    if (o.line > 0){
      head = document.createElement("div");
      head.className = "amd-head";
      head.style.height = o.line + "px";
      host.appendChild(head);
    }
  }

  /* ---- the tracking fault ---------------------------------------------- */
  if (tear){
    var slip = null;
    setInterval(function(){
      if (document.hidden || Math.random() > 0.55) return;
      var top = 8 + Math.random() * 68;
      var band = 4 + Math.random() * 12;
      tear.style.clipPath = "inset(" + top.toFixed(1) + "% 0 " +
                            (100 - top - band).toFixed(1) + "% 0)";
      // left, not transform: the pictures are centred with translateX(-50%)
      tear.style.left = "calc(50% + " +
                        ((Math.random() * 2 - 1) * o.amp).toFixed(1) + "px)";
      tear.style.filter = "brightness(1.35) saturate(.7)";
      tear.style.opacity = "1";
      clearTimeout(slip);
      slip = setTimeout(function(){ tear.style.opacity = "0"; },
                        70 + Math.random() * 150);
    }, 620);
  }

  if (!o.scan) return {swap: put, set: put};

  /* ---- drawing the new expression in ------------------------------------ */
  var busy = null;
  function clip(v, ms){
    for (var i = 0; i < list.length; i++){
      list[i].style.transition = ms ? ("clip-path " + ms + "ms steps(" + o.steps + ")") : "none";
      list[i].style.clipPath = v;
    }
  }
  function done(){
    for (var i = 0; i < list.length; i++){
      list[i].style.transition = "";
      list[i].style.clipPath = "";
    }
    if (head) head.style.opacity = "0";
    busy = null;
  }

  function swap(src){
    // Nothing to draw if the picture is not actually changing, and a sweep
    // already running just carries on with the newer picture rather than
    // starting over on top of itself.
    if (!src || src === list[0].getAttribute("src") || busy){
      put(src);
      return;
    }
    put(src);
    clip("inset(0 0 100% 0)", 0);       // empty: only the raster is left
    raster.style.opacity = "1";
    var beat = Math.min(220, Math.max(60, Math.round(o.ms * 0.3)));
    busy = setTimeout(function(){
      raster.style.opacity = "0";
      if (head){
        head.style.opacity = "1";
        if (head.animate){
          head.animate([{top: (-o.line) + "px"}, {top: host.clientHeight + "px"}],
                       {duration: o.ms, easing: "steps(" + o.steps + ")"});
        }
      }
      // one frame with the clip parked, then the transition has something to run
      requestAnimationFrame(function(){
        requestAnimationFrame(function(){ clip("inset(0 0 0 0)", o.ms); });
      });
      busy = setTimeout(done, o.ms + 60);
    }, beat);
  }

  return {swap: swap, set: put};
}
"""
