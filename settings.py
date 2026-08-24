# SPDX-License-Identifier: MIT
"""A form for the settings people actually change.

config.json holds fifty-odd keys and stays the place for everything: the
dialogue pools, the mood maps, several providers, the tuning nobody touches
twice. Asking someone to edit JSON to make her quieter is asking them not to
bother.

So this is deliberately not a mirror of the file. It carries the fields worth
reaching for and leaves the rest alone -- including keys it has never heard of,
which are written back untouched. There is a button to the raw config for
everything else.
"""

from __future__ import annotations

import copy
import json
import os
from typing import Any

from aqt import mw
from aqt.qt import (
    QCheckBox, QComboBox, QDesktopServices, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
    QPushButton, QSpinBox, QTabWidget, QUrl, QVBoxLayout, QWidget, Qt,
)
from aqt.utils import askUser, showInfo, tooltip

PACKAGE = __name__.split(".")[0]

# Anki re-serialises an add-on's config with sort_keys=True before showing it,
# so anything stored to mark a section just sorts to the top away from what it
# was marking. The headings are therefore not stored at all: they are inserted
# into the text on its way to the editor and taken out again on its way back,
# which also keeps them out of anyone's saved config.
MARK = "====="

GROUPS: list[tuple[str, list[str]]] = [
    ("TAMPILAN", ["theme", "theme_deck_list", "theme_bars", "hide_bottom_bar",
                  "daily_target"]),
    ("PANEL DI LAYAR DECK",
     ["show_on_deck_list", "panel_width", "panel_height", "deck_scroll",
      "deck_max_height", "show_stats", "show_history", "history_days",
      "show_note", "right_width"]),
    ("SAAT REVIEW",
     ["show_in_reviewer", "reviewer_size", "reviewer_corner",
      "reviewer_always_visible", "reviewer_hide_seconds"]),
    ("ANIMASI & SUARA",
     ["effects", "grain_opacity", "chatter_seconds", "typewriter", "typewriter_speed",
      "dialog_mouth", "dialog_mouth_ms", "blink", "blink_min_ms",
      "blink_max_ms", "blink_hold_ms", "dialog_caret", "dialog_caret_char",
      "dialog_sound", "dialog_volume", "dialog_pitch", "dialog_every"]),
    ("AI / CHAT",
     ["character_name", "user_name", "chat_enabled", "chat_shortcut", "chat_width", "chat_face_height", "chat_thumb_expression", "chat_thumb_zoom", "chat_thumb_y",
      "active_provider", "providers", "persona", "about_you",
      "remember_chat", "remember_messages", "compact_history",
      "send_study_context",
      "send_card_context", "max_context_chars", "max_history_turns",
      "max_tokens", "timeout_seconds"]),
    ("KALIMAT & EKSPRESI",
     ["lines", "moods", "reviewer_lines", "reviewer_moods", "chat_moods"]),
    ("LAIN-LAIN", ["check_updates"]),
]

# Enough of our own keys to be sure the text on screen is ours. The display hook
# is handed the JSON without being told whose it is, and reshaping somebody
# else's config would be a genuinely nasty thing to do.
FINGERPRINT = ("reviewer_moods", "chat_moods", "dialog_mouth", "reviewer_corner",
               "chatter_seconds")


def _grouped(data):
    out = {}
    placed = set()
    for title, keys in GROUPS:
        present = [k for k in keys if k in data]
        if not present:
            continue
        out["%s  %s  %s" % (MARK, title, MARK)] = ""
        for k in present:
            out[k] = data[k]
            placed.add(k)
    rest = [k for k in data if k not in placed and not k.startswith(MARK)]
    if rest:
        out["%s  LAINNYA  %s" % (MARK, MARK)] = ""
        for k in rest:
            out[k] = data[k]
    return json.dumps(out, ensure_ascii=False, indent=4, separators=(",", ": "))


def on_display_json(text):
    """Group the raw editor's contents. Ours only, and never at the cost of
    showing something that will not parse: any trouble and the text is returned
    exactly as it arrived."""
    try:
        data = json.loads(text)
    except Exception:
        return text
    if not isinstance(data, dict):
        return text
    if sum(1 for k in FINGERPRINT if k in data) < 4:
        return text
    try:
        return _grouped(data)
    except Exception:
        return text


def on_update_json(text, addon):
    """Take the headings back out, so they never reach anyone's saved config."""
    if addon != PACKAGE:
        return text
    try:
        data = json.loads(text)
    except Exception:
        return text          # let Anki report the syntax error itself
    if not isinstance(data, dict):
        return text
    kept = {k: v for k, v in data.items() if not k.startswith(MARK)}
    return json.dumps(kept, ensure_ascii=False, indent=4)


# (key, label, kind, *args). Order here is the order on screen.
TABS: list[tuple[str, list[tuple]]] = [
    ("Tampilan", [
        ("theme", "Tema", "choice", None),
        ("daily_target", "Target kartu per hari", "int", 10, 5000),
        ("theme_deck_list", "Ikut mewarnai daftar deck", "bool"),
        ("theme_bars", "Ikut mewarnai bilah atas & bawah", "bool"),
        ("show_on_deck_list", "Tampilkan dia di layar deck", "bool"),
        ("panel_width", "Lebar panelnya (px)", "int", 120, 600),
        ("panel_height", "Tinggi panelnya (px)", "int", 200, 1200),
        ("show_stats", "Tampilkan statistik", "bool"),
        ("show_history", "Tampilkan grafik 14 hari", "bool"),
        ("show_note", "Tampilkan catatan harian", "bool"),
    ]),
    ("Animasi & suara", [
        ("effects", "Efek glitch dan noise", "bool"),
        ("grain_opacity", "Kekuatan butiran di panel chat (0 = mati)",
         "float", 0.0, 1.0, 0.05),
        ("typewriter", "Kalimat diketik huruf per huruf", "bool"),
        ("typewriter_speed", "Kecepatan ketik (ms per huruf, kecil = cepat)",
         "int", 5, 200),
        ("dialog_mouth", "Mulutnya bergerak saat bicara", "bool"),
        ("blink", "Matanya berkedip sesekali", "bool"),
        ("dialog_mouth_ms", "Kecepatan mulut (ms per frame)", "int", 40, 400),
        ("dialog_caret", "Kursor kedip di ujung teks", "bool"),
        ("dialog_sound", "Suara bicara 8-bit", "bool"),
        ("dialog_volume", "Volume suara (0 - 1)", "float", 0.0, 1.0, 0.02),
        ("dialog_pitch", "Nada suara (Hz, besar = lebih tinggi)", "int", 80, 2000),
        ("chatter_seconds", "Ganti kalimat sendiri tiap (detik)", "int", 5, 600),
    ]),
    ("Saat review", [
        ("show_in_reviewer", "Tampilkan dia saat review", "bool"),
        ("reviewer_always_visible", "Tetap terlihat, bukan cuma saat menjawab",
         "bool"),
        ("reviewer_corner", "Posisinya", "choice",
         [("bottom-right", "Kanan bawah"), ("bottom-left", "Kiri bawah"),
          ("top-right", "Kanan atas"), ("top-left", "Kiri atas")]),
        ("reviewer_size", "Ukurannya (px)", "int", 90, 500),
        ("reviewer_hide_seconds", "Kalimatnya hilang setelah (detik)", "int", 1, 60),
    ]),
    ("Chat / AI", [
        ("character_name", "Namanya", "text"),
        ("user_name", "Panggil kamu apa (kosong = nama profil Anki)", "text"),
        ("chat_enabled", "Aktifkan chat", "bool"),
        ("chat_shortcut", "Tombol pintas", "text"),
        ("chat_width", "Lebar panel chat (px)", "int", 280, 1200),
        ("chat_face_height", "Tinggi potret di panel chat (px)", "int", 90, 600),
        ("chat_thumb_expression",
         "Potret kecil ikut ekspresi tiap kalimat (mati = selalu wajah normal)",
         "bool"),
        ("__provider__", "", "provider"),
        ("persona", "Siapa dia (persona) - {name} dan {user} akan diganti", "longtext"),
        ("about_you", "Yang perlu dia ingat tentang kamu", "longtext"),
        ("remember_chat", "Ingat percakapan setelah Anki ditutup", "bool"),
        ("compact_history",
         "Ringkas percakapan lama, jangan dibuang (butuh 1 permintaan tambahan)",
         "bool"),
        ("send_study_context", "Beri tahu dia angka belajarmu hari ini", "bool"),
        ("send_card_context", "Beri tahu dia kartu yang sedang terbuka", "bool"),
    ]),
    ("Lain-lain", [
        ("check_updates", "Cek versi baru sekali sehari", "bool"),
    ]),
]

PROVIDER_HINT = (
    "Model yang menjawab. <b>Alamat API</b> untuk OpenRouter: "
    "<code>https://openrouter.ai/api/v1</code>"
)


class Settings(QDialog):
    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.setWindowTitle("Amadeus Deck - Pengaturan")
        self.setMinimumWidth(520)
        self.raw: dict[str, Any] = mw.addonManager.getConfig(PACKAGE) or {}
        self.widgets: dict[str, Any] = {}

        outer = QVBoxLayout(self)
        tabs = QTabWidget(self)
        for title, fields in TABS:
            tabs.addTab(self._tab(fields), title)
        outer.addWidget(tabs)

        row = QHBoxLayout()
        advanced = QPushButton("Config lanjutan…", self)
        advanced.setToolTip("Semua pengaturan, termasuk kalimat dan ekspresinya")
        advanced.clicked.connect(self._advanced)
        row.addWidget(advanced)
        row.addStretch(1)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel, self)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        row.addWidget(buttons)
        outer.addLayout(row)

    # -------------------------------------------------------------- building

    def _tab(self, fields):
        page = QWidget(self)
        form = QFormLayout(page)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        for spec in fields:
            key, label, kind = spec[0], spec[1], spec[2]
            if kind == "provider":
                self._provider_rows(form)
                continue
            widget = self._widget(key, kind, spec[3:])
            self.widgets[key] = (kind, widget)
            if kind == "bool":
                widget.setText(label)
                form.addRow("", widget)
            elif kind == "longtext":
                form.addRow(QLabel(label + ":"))
                form.addRow(widget)
            else:
                form.addRow(label + ":", widget)
        return page

    def _widget(self, key, kind, args):
        value = self.raw.get(key)
        if kind == "bool":
            w = QCheckBox(self)
            w.setChecked(bool(value) if value is not None else True)
            return w
        if kind == "int":
            w = QSpinBox(self)
            w.setRange(args[0], args[1])
            try:
                w.setValue(int(value))
            except (TypeError, ValueError):
                w.setValue(args[0])
            return w
        if kind == "float":
            w = QDoubleSpinBox(self)
            w.setRange(args[0], args[1])
            w.setSingleStep(args[2])
            w.setDecimals(2)
            try:
                w.setValue(float(value))
            except (TypeError, ValueError):
                w.setValue(args[0])
            return w
        if kind == "choice":
            w = QComboBox(self)
            # None means "ask the theme table", so a new theme never needs a
            # second list here to be remembered.
            options = args[0]
            if options is None:
                from . import theme as theme_mod
                options = theme_mod.choices()
            for real, shown in options:
                w.addItem(shown, real)
            index = w.findData(value)
            w.setCurrentIndex(max(0, index))
            return w
        if kind == "longtext":
            w = QPlainTextEdit(self)
            w.setPlainText(str(value or ""))
            w.setMinimumHeight(130)
            return w
        w = QLineEdit(self)
        w.setText(str(value or ""))
        return w

    def _provider_rows(self, form):
        """The whole list, editable here.

        This began as one provider on the grounds that anyone needing several
        was comfortable in the raw config. That was wrong the moment a second
        one shipped: adding a model meant hand-editing JSON, which is precisely
        what this form exists to avoid.
        """
        self.providers = [copy.deepcopy(p)
                          for p in (self.raw.get("providers") or [])
                          if isinstance(p, dict)]
        self.p_index = self._active_index()

        self.p_pick = QComboBox(self)
        self.p_pick.currentIndexChanged.connect(self._switch_provider)
        add = QPushButton("+ Tambah", self)
        add.setToolTip("Buat entri model baru")
        add.clicked.connect(self._add_provider)
        drop = QPushButton("Hapus", self)
        drop.setToolTip("Hapus entri ini")
        drop.clicked.connect(self._drop_provider)
        bar = QWidget(self)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.addWidget(self.p_pick, 1)
        bl.addWidget(add)
        bl.addWidget(drop)
        form.addRow("Model yang dipakai:", bar)

        hint = QLabel(PROVIDER_HINT, self)
        hint.setWordWrap(True)
        form.addRow(hint)

        self.p_name = QLineEdit(self)
        self.p_model = QLineEdit(self)
        self.p_url = QLineEdit(self)
        self.p_window = QSpinBox(self)
        self.p_window.setRange(0, 4000000)
        self.p_window.setSingleStep(1024)
        self.p_window.setSpecialValueText("belum diisi")
        self.p_window.setToolTip(
            "Jendela konteks model, dipakai untuk meteran di panel chat. "
            "Biarkan 0 kalau tidak tahu.")
        self.p_key = QLineEdit(self)
        self.p_key.setEchoMode(QLineEdit.EchoMode.Password)
        show = QPushButton("Lihat", self)
        show.setCheckable(True)
        show.toggled.connect(lambda on: self.p_key.setEchoMode(
            QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password))
        keyrow = QWidget(self)
        kl = QHBoxLayout(keyrow)
        kl.setContentsMargins(0, 0, 0, 0)
        kl.addWidget(self.p_key, 1)
        kl.addWidget(show)

        help_btn = QPushButton("Cara dapat API key? →", self)
        help_btn.setToolTip("Membuka panduan di browser (tersedia Indonesia & English)")
        help_btn.clicked.connect(open_guide)
        self.test_btn = QPushButton("Tes koneksi", self)
        self.test_btn.setToolTip(
            "Kirim satu permintaan kecil dan tampilkan apa adanya jawabannya")
        self.test_btn.clicked.connect(self._test_provider)
        helprow = QWidget(self)
        hr = QHBoxLayout(helprow)
        hr.setContentsMargins(0, 0, 0, 0)
        hr.addWidget(help_btn, 1)
        hr.addWidget(self.test_btn)
        form.addRow("", helprow)

        form.addRow("Nama:", self.p_name)
        form.addRow("Model:", self.p_model)
        form.addRow("Alamat API:", self.p_url)
        form.addRow("Jendela konteks:", self.p_window)
        form.addRow("API key:", keyrow)

        self._refill_picker()
        self._load_provider(self.p_index)

    # ------------------------------------------------------------- providers

    def _active_index(self):
        wanted = str(self.raw.get("active_provider") or "").strip()
        for i, p in enumerate(self.providers):
            if str(p.get("name", "")).strip() == wanted:
                return i
        return 0 if self.providers else -1

    def _active_provider(self):
        entries = [p for p in (self.raw.get("providers") or []) if isinstance(p, dict)]
        wanted = str(self.raw.get("active_provider") or "").strip()
        for p in entries:
            if str(p.get("name", "")).strip() == wanted:
                return p
        return entries[0] if entries else {}

    def _refill_picker(self):
        self.p_pick.blockSignals(True)
        self.p_pick.clear()
        for i, p in enumerate(self.providers):
            self.p_pick.addItem(str(p.get("name") or "Provider %d" % (i + 1)))
        if not self.providers:
            self.p_pick.addItem("(belum ada)")
        self.p_pick.setCurrentIndex(max(0, self.p_index))
        self.p_pick.blockSignals(False)

    def _load_provider(self, index):
        blank = not (0 <= index < len(self.providers))
        entry = {} if blank else self.providers[index]
        for widget, key in ((self.p_name, "name"), (self.p_model, "model"),
                            (self.p_url, "base_url"), (self.p_key, "api_key")):
            widget.setText(str(entry.get(key) or ""))
            widget.setEnabled(not blank)
        try:
            self.p_window.setValue(int(entry.get("context_window") or 0))
        except (TypeError, ValueError):
            self.p_window.setValue(0)
        self.p_window.setEnabled(not blank)

    def _stash_provider(self):
        """Fold what is on screen back into the list, so switching entries does
        not quietly throw away an edit."""
        if not (0 <= self.p_index < len(self.providers)):
            return
        entry = self.providers[self.p_index]
        entry["name"] = self.p_name.text().strip() or entry.get("name") or "Provider"
        entry["model"] = self.p_model.text().strip()
        entry["base_url"] = self.p_url.text().strip()
        entry["api_key"] = self.p_key.text().strip()
        entry["context_window"] = self.p_window.value()
        entry.setdefault("kind", "openai")

    def _switch_provider(self, index):
        self._stash_provider()
        self.p_index = index
        self._load_provider(index)
        self._refill_picker()

    def _add_provider(self):
        self._stash_provider()
        self.providers.append({"name": "Model baru", "kind": "openai",
                               "model": "", "base_url": "", "api_key": ""})
        self.p_index = len(self.providers) - 1
        self._refill_picker()
        self._load_provider(self.p_index)
        self.p_name.setFocus()
        self.p_name.selectAll()

    def _test_provider(self):
        """Send one tiny request and show exactly what came back.

        "400 model is unavailable" from inside a chat panel says nothing about
        which of the four fields is wrong, or whether the fault is the account
        rather than the settings. One button that reports the answer verbatim
        beats guessing at it.
        """
        from . import chatconf, providers

        self._stash_provider()
        if not (0 <= self.p_index < len(self.providers)):
            return
        entry = chatconf.normalize_provider(self.providers[self.p_index])
        try:
            key = chatconf.resolve_api_key(entry)
        except chatconf.KeyLookupError as exc:
            showInfo(str(exc))
            return

        got = []
        self.test_btn.setEnabled(False)
        self.test_btn.setText("Menunggu…")

        def work():
            providers.stream_completion(
                entry, key, "Balas dengan satu kata: ok.",
                [{"role": "user", "content": "ping"}],
                max_tokens=16, timeout=30,
                on_text=got.append, on_status=lambda _c: None,
                should_stop=lambda: False)

        def done(future):
            self.test_btn.setEnabled(True)
            self.test_btn.setText("Tes koneksi")
            try:
                future.result()
            except Exception as exc:      # noqa: BLE001 - shown verbatim
                showInfo("Gagal.\n\nModel: %s\nAlamat: %s\n\n%s"
                         % (entry["model"], entry["base_url"], exc))
                return
            reply = "".join(got).strip()
            showInfo("Berhasil.\n\nModel: %s\nJawabannya: %s"
                     % (entry["model"], reply[:120] or "(kosong)"))

        mw.taskman.run_in_background(work, done)

    def _drop_provider(self):
        if not (0 <= self.p_index < len(self.providers)):
            return
        entry = self.providers[self.p_index]
        name = entry.get("name") or "entri ini"
        # Losing a key means going back to the service to make another, so this
        # one asks first even though nothing else here does.
        if str(entry.get("api_key") or "").strip():
            if not askUser("Hapus \"%s\"?\n\nAPI key-nya ikut terhapus." % name):
                return
        del self.providers[self.p_index]
        self.p_index = min(self.p_index, len(self.providers) - 1)
        self._refill_picker()
        self._load_provider(self.p_index)

    # ---------------------------------------------------------------- saving

    def _save(self):
        for key, (kind, widget) in self.widgets.items():
            if kind == "bool":
                self.raw[key] = widget.isChecked()
            elif kind in ("int", "float"):
                self.raw[key] = widget.value()
            elif kind == "choice":
                self.raw[key] = widget.currentData()
            elif kind == "longtext":
                self.raw[key] = widget.toPlainText()
            else:
                self.raw[key] = widget.text().strip()

        self._stash_provider()
        # Entries keep any field this form never shows -- api_key_env,
        # system_in_user, extra_headers -- because they were edited in place.
        self.raw["providers"] = self.providers
        if 0 <= self.p_index < len(self.providers):
            self.raw["active_provider"] = self.providers[self.p_index].get("name", "")

        mw.addonManager.writeConfig(PACKAGE, self.raw)
        self._refresh()
        tooltip("Pengaturan disimpan.", period=3000)
        self.accept()

    def _refresh(self):
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

    def _advanced(self):
        self.reject()
        open_raw()


GUIDE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "guide", "apikey.html")


def open_guide():
    """Opened in the user's own browser rather than a Qt window: it is a page
    with links they will want to follow, and following a link out of an Anki
    dialog goes nowhere useful."""
    if not os.path.exists(GUIDE):
        showInfo("Panduannya tidak ketemu di:\n%s" % GUIDE)
        return
    # Anki's own media server, not a file:// path. Inside a Flatpak the browser
    # is handed the file through the document portal, which exports that single
    # file and nothing beside it -- the guide's images are not in the exported
    # directory and never load. Over http the whole folder is reachable, and
    # there is no cached copy of a previous version to fight either.
    try:
        port = mw.mediaServer.getPort()
    except Exception:
        port = 0
    if port:
        QDesktopServices.openUrl(QUrl(
            "http://127.0.0.1:%d/_addons/%s/guide/apikey.html" % (port, PACKAGE)))
        return
    QDesktopServices.openUrl(QUrl.fromLocalFile(GUIDE))


_raw_holder = None


def open_raw():
    """Anki's own JSON editor, for everything this form leaves out.

    It only wants the add-on manager from whichever dialog opened it, so a
    stand-in is enough. Building the whole Add-ons window just to reach the
    editor would put a list of every add-on on screen that nobody asked for.
    """
    global _raw_holder

    from aqt.addons import ConfigEditor

    conf = mw.addonManager.getConfig(PACKAGE)
    if conf is None:
        showInfo("Add-on ini tidak punya config.")
        return
    _raw_holder = QDialog(mw)          # kept alive: it parents the editor
    _raw_holder.mgr = mw.addonManager
    ConfigEditor(_raw_holder, PACKAGE, conf)


def open_dialog():
    Settings(mw).exec()
    return True                        # Anki reads False as "not handled"


_submenu = None


def tools_menu():
    """The add-on's one entry in Tools, created by whichever module asks first.

    Two top-level items both beginning with "Amadeus" read as two add-ons -- and
    did, to the person using it. Everything the add-on offers hangs off one
    name, the way the larger add-ons here do it.
    """
    global _submenu

    if _submenu is None:
        _submenu = mw.form.menuTools.addMenu("Amadeus Deck")
    return _submenu


def register():
    from aqt import gui_hooks
    from aqt.qt import QAction

    # Clicking Config in the Add-ons list lands on the form, not on raw JSON.
    # The people who reach for that button are exactly the ones the form is for.
    try:
        mw.addonManager.setConfigAction(PACKAGE, open_dialog)
    except Exception:
        pass
    gui_hooks.addon_config_editor_will_display_json.append(on_display_json)
    gui_hooks.addon_config_editor_will_update_json.append(on_update_json)

    def setup():
        act = QAction("Pengaturan…", mw)
        act.triggered.connect(lambda _=False: open_dialog())
        tools_menu().addAction(act)

    gui_hooks.main_window_did_init.append(setup)
