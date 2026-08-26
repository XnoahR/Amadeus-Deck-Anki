"""Her lines, spoken out loud instead of beeped.

The eight-bit blip is a stand-in for a voice. If there are real recordings on
disk, they are the voice, and the blip steps aside for that line.

A clip is found by hashing the line it belongs to, not by its position in the
pool. Edit a line in the config and the link breaks by itself: the result is
silence for that line, never the wrong sentence in her voice. Nothing is
shipped -- the folder starts empty, and an empty folder simply means the blip
keeps its job.
"""
import hashlib
import os

FOLDER = "voice"
KINDS = (".ogg", ".mp3", ".wav", ".m4a")


def slug(line):
    """Which file belongs to this line."""
    return hashlib.sha1((line or "").encode("utf-8")).hexdigest()[:10]


def folder(addon_dir):
    return os.path.join(addon_dir, "user_files", FOLDER)


def on_disk(addon_dir):
    """-> {id: filename} for whatever is actually there."""
    out = {}
    try:
        names = os.listdir(folder(addon_dir))
    except OSError:
        return out
    for name in sorted(names):
        stem, ext = os.path.splitext(name)
        if ext.lower() in KINDS:
            out.setdefault(stem, name)
    return out


def urls(addon, addon_dir, pools, shown):
    """-> {line as displayed: url}

    Keyed by the text after the numbers are filled in, because that is the
    string the page has in hand at the moment it speaks. The lookup on disk
    still uses the raw line, so a clip survives the count changing.
    """
    have = on_disk(addon_dir)
    out = {}
    for lines in (pools or {}).values():
        for raw in lines or []:
            name = have.get(slug(raw))
            if name:
                out[shown(raw)] = "/_addons/%s/user_files/%s/%s" % (addon, FOLDER, name)
    return out


def react_urls(addon, addon_dir):
    """-> {mood: [url, ...]} for the short reaction clips.

    Keyed by mood rather than by line, because these answer *how* she felt, not
    *what* she said -- the same "mou ikkai" fits every wrong answer. The index
    is written next to the clips by whoever generated them; a missing or broken
    index just means no reactions, never a crash.
    """
    import json
    path = os.path.join(folder(addon_dir), "react.json")
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    have = set(os.listdir(folder(addon_dir)))
    out = {}
    for mood, items in data.items():
        urls = []
        for it in items or []:
            name = it.get("file") if isinstance(it, dict) else it
            if isinstance(name, str) and name in have:
                urls.append("/_addons/%s/user_files/%s/%s" % (addon, FOLDER, name))
        if urls:
            out[str(mood)] = urls
    return out


def settings(cfg):
    try:
        vol = float(cfg.get("voice_clips_volume", 0.9))
    except (TypeError, ValueError):
        vol = 0.9
    return {
        "on": bool(cfg.get("voice_clips", False)),
        "vol": max(0.0, min(1.0, vol)),
        "hush": bool(cfg.get("voice_clips_hush", True)),
    }


JS = r"""
// amdClips(map, opts) -> {play(text) -> true if the blips should stand down}
function amdClips(map, o){
  o = o || {};
  var cur = null;
  if (!o.on || !map) return {play: function(){ return false; }};
  return {
    play: function(text){
      var url = map[text];
      if (!url) return false;
      try {
        // One voice at a time: a new line cuts the old one off rather than
        // talking over it.
        if (cur) { cur.pause(); }
        cur = new Audio(url);
        cur.volume = o.vol == null ? 0.9 : o.vol;
        var p = cur.play();
        // Before the page has been clicked the browser refuses to start audio.
        // That rejection is expected, not an error worth shouting about -- but
        // the blips should not be silenced for a line nobody could hear.
        if (p && p.catch) { p.catch(function(){}); }
      } catch (e) { return false; }
      return !!o.hush;
    }
  };
}
"""
