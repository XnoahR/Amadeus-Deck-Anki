# SPDX-License-Identifier: AGPL-3.0-or-later
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

from typing import Any

from aqt import mw
from aqt.qt import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton, QSpinBox,
    QTabWidget, QVBoxLayout, QWidget, Qt,
)
from aqt.utils import showInfo, tooltip

PACKAGE = __name__.split(".")[0]

# (key, label, kind, *args). Order here is the order on screen.
TABS: list[tuple[str, list[tuple]]] = [
    ("Tampilan", [
        ("theme", "Tema", "choice",
         [("vhs", "VHS retro"), ("holo", "Holo biru")]),
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
        ("typewriter", "Kalimat diketik huruf per huruf", "bool"),
        ("typewriter_speed", "Kecepatan ketik (ms per huruf, kecil = cepat)",
         "int", 5, 200),
        ("dialog_mouth", "Mulutnya bergerak saat bicara", "bool"),
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
        ("chat_enabled", "Aktifkan chat", "bool"),
        ("chat_shortcut", "Tombol pintas", "text"),
        ("chat_width", "Lebar panel chat (px)", "int", 280, 1200),
        ("chat_face_height", "Tinggi potret di panel chat (px)", "int", 90, 600),
        ("__provider__", "", "provider"),
        ("persona", "Siapa dia (persona)", "longtext"),
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
            for real, shown in args[0]:
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
        """One provider, not the whole list. Someone who needs several is
        already in the raw config, and putting a list editor here would make
        this page look exactly like the thing it exists to avoid."""
        entry = self._active_provider()
        hint = QLabel(PROVIDER_HINT, self)
        hint.setWordWrap(True)
        form.addRow(hint)

        self.p_name = QLineEdit(str(entry.get("name") or ""), self)
        self.p_model = QLineEdit(str(entry.get("model") or ""), self)
        self.p_url = QLineEdit(str(entry.get("base_url") or ""), self)
        self.p_key = QLineEdit(str(entry.get("api_key") or ""), self)
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

        form.addRow("Nama:", self.p_name)
        form.addRow("Model:", self.p_model)
        form.addRow("Alamat API:", self.p_url)
        form.addRow("API key:", keyrow)

    def _active_provider(self):
        entries = [p for p in (self.raw.get("providers") or []) if isinstance(p, dict)]
        wanted = str(self.raw.get("active_provider") or "").strip()
        for p in entries:
            if str(p.get("name", "")).strip() == wanted:
                return p
        return entries[0] if entries else {}

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

        name = self.p_name.text().strip()
        if name or self.p_model.text().strip() or self.p_key.text().strip():
            name = name or "Model saya"
            entries = [p for p in (self.raw.get("providers") or [])
                       if isinstance(p, dict)]
            target = None
            for p in entries:
                if str(p.get("name", "")).strip() == str(
                        self._active_provider().get("name", "")).strip():
                    target = p
                    break
            if target is None:
                target = {"kind": "openai"}
                entries.append(target)
            target["name"] = name
            target["kind"] = target.get("kind") or "openai"
            target["model"] = self.p_model.text().strip()
            target["base_url"] = self.p_url.text().strip()
            target["api_key"] = self.p_key.text().strip()
            self.raw["providers"] = entries
            self.raw["active_provider"] = name

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


def register():
    from aqt import gui_hooks
    from aqt.qt import QAction

    # Clicking Config in the Add-ons list lands on the form, not on raw JSON.
    # The people who reach for that button are exactly the ones the form is for.
    try:
        mw.addonManager.setConfigAction(PACKAGE, open_dialog)
    except Exception:
        pass

    def setup():
        act = QAction("Amadeus: pengaturan…", mw)
        act.triggered.connect(lambda _=False: open_dialog())
        mw.form.menuTools.addAction(act)

    gui_hooks.main_window_did_init.append(setup)
