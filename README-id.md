# Amadeus Deck

[English](README.md)

Addon Anki yang menaruh karakter di layar deck dan di samping kartu saat kamu
review. Dia bereaksi mengikuti jalannya sesi: senang kalau jawabanmu benar,
kelihatan kesal kalau kamu tekan Again lima kali beruntun, dan kecewa kalau
streak-mu putus.

Terinspirasi dari Project Amadeus di Steins;Gate 0.

![Amadeus Deck di layar deck](docs/screenshot.png)

*Karakter di gambar tidak ikut dalam unduhan — lihat [Pakai karaktermu sendiri](#pakai-karaktermu-sendiri).*

**Note type kamu tidak disentuh sama sekali.** Tidak ada template yang diubah,
tidak ada yang ditambahkan ke kartumu, dan potret saat review hidup di dalam
Shadow DOM sehingga CSS kartumu dan addon ini tidak bisa saling menjangkau.
Hapus addon-nya, koleksimu persis seperti semula.

---

## Pakai karaktermu sendiri

Addon ini dikirim **tanpa gambar sama sekali**. Taruh gambarmu di folder
`character/` di dalam folder addon:

```
<data anki>/addons21/amadeus_deck/character/
```

Beri nama file yang **diakhiri nama ekspresi dan angka**:

```
myoc_happy1.png   myoc_annoyed2.png   myoc_sided_thinking1.png
```

Awalannya bebas — yang dibaca cuma akhirannya. Lebih dari satu file per ekspresi
lebih bagus; salah satunya diambil acak supaya wajahnya tidak itu-itu saja.

**Ekspresi yang dicari**

Hadap depan: `normal` `happy` `winking` `blush` `disappointed` `sad` `annoyed`
`pissed` `angry` `eyes_closed` `indifferent`

Hadap samping: `side` `sided_pleasant` `sided_thinking` `sided_blush`
`sided_worried` `sided_surprised`

Yang benar-benar wajib cuma `normal` — sisanya otomatis mundur ke situ kalau
tidak ada. Cek punyamu dengan:

```
python3 check_character.py
```

Dia melaporkan ekspresi mana yang sudah ada, state mana yang terpaksa memakai
pengganti, dan apakah ukuran serta transparansi filemu konsisten.

**Format yang disarankan:** PNG dengan latar transparan, potret sekitar 454×810,
kepala dekat tepi atas. Ukuran yang campur-campur bikin potretnya melompat
setiap ganti ekspresi.

> Art karakter biasanya milik hak cipta orang lain. Itu sebabnya tidak ada satu
> pun yang dibundel di sini: apa yang kamu simpan di komputer sendiri itu
> urusanmu, tapi repo yang menyebarkan karakter orang lain itu soal berbeda.
> Cara ini juga bikin setiap orang bisa memakai karakter yang benar-benar mereka
> mau.

---

## Apa saja yang ditambahkan

**Di layar deck** — potret di samping daftar deck, kartu ringkasan (review hari
ini, waktu, streak, tunggakan, akurasi), grafik batang beberapa hari terakhir,
dan catatan harian yang menyimpan dirinya sendiri sambil kamu mengetik. Daftar
decknya ikut bertema dan bisa di-scroll, bukan memanjang ke bawah.

**Saat review** — potretnya duduk di pojok dan berganti ekspresi mengikuti
jawabanmu. Tekan Again tiga kali beruntun dia mulai kesal; lima kali dia
menyuruhmu istirahat.

**Dua tema** — `vhs` (magenta/cyan, garis tracking pita video) dan `holo`
(hologram cyan/magenta dengan potongan meleset). Dua-duanya punya scanline dan
noise yang bisa dimatikan.

---

## Pengaturan

Semua ada di **Tools → Add-ons → Amadeus Deck → Config**. Seluruh dialognya juga
di situ, jadi kamu bisa menulis ulang setiap kalimat dengan suara karaktermu
sendiri tanpa menyentuh kode:

```json
"lines": {
  "behind": ["Sisa {due}. Baru {done} dari {target}."],
  "target": ["Target {target} tercapai. ...Kerja bagus."]
}
```

Angka yang bisa disisipkan: `{due}` sisa kartu, `{done}` sudah dikerjakan,
`{target}` target harian, `{streak}` hari beruntun.

Ubah satu state, sisanya tetap memakai bawaan. Hapus satu state, bawaannya
kembali dipakai. Kalau kamu salah tulis placeholder, kalimatnya tampil apa
adanya — layar decknya tidak ikut rusak.

**State di layar deck**

| State | Kapan muncul |
|---|---|
| `reminder` | belum review sama sekali hari ini |
| `behind` | sudah mulai tapi masih jauh dari target |
| `close` | sudah 75% target |
| `target` | target tercapai |
| `clear` | semua deck kosong |
| `broken` | streak putus |
| `poke` | kamu klik gambarnya |
| `chatter` | didiamkan beberapa saat |

**State saat review:** `good` `easy` `hard` `wrong` `annoyed` (Again 3×)
`pissed` (Again 5×) `poke` `idle`

Opsi lain yang sering dipakai: `theme`, `daily_target`, `effects`,
`panel_width`, `panel_height`, `deck_scroll`, `deck_max_height`, `show_stats`,
`show_history`, `show_note`, `show_in_reviewer`, `reviewer_corner`,
`reviewer_size`, `reviewer_always_visible`. Penjelasan lengkapnya ada di tab
Config.

---

## Cara pasang

**Cara gampang.** Unduh
[`AmadeusDeck.ankiaddon`](https://github.com/XnoahR/Amadeus-Deck-Anki/releases/latest/download/AmadeusDeck.ankiaddon)
lalu klik dua kali, atau lewat Anki: **Tools → Add-ons → Install from file**.

Setelah itu taruh gambarmu: **Tools → Add-ons → Amadeus Deck → View Files**,
masukkan ke folder `character/`, lalu restart Anki.

**Dari source.** Kalau mau menyalin foldernya sendiri ke direktori addon Anki:

```
~/.local/share/Anki2/addons21/amadeus_deck              # Linux
~/.var/app/net.ankiweb.Anki/data/Anki2/addons21/...     # Linux, Flatpak
%APPDATA%\Anki2\addons21\amadeus_deck                   # Windows
~/Library/Application Support/Anki2/addons21/...        # macOS
```

Lalu taruh gambarmu di `character/` dan restart sekali lagi.

Dibuat dan diuji di Anki 25.09. **Desktop saja** — layar deck dan overlay
reviewer disuntikkan ke web view milik Anki, dan AnkiDroid maupun AnkiMobile
tidak punya itu. Kartumu tetap sync seperti biasa; dia cuma tidak membawa
tampilan ini.

---

## Yang perlu kamu tahu di depan

- **Update Anki bisa merusaknya.** Layar deck ditata dengan mendefinisikan ulang
  CSS variable milik Anki dan membungkus tabel decknya. Dua-duanya bagian dalam
  Anki yang bisa berubah kapan saja tanpa pemberitahuan.
- **Statistiknya diambil dari `revlog`**, tabel yang sama yang dipakai Anki,
  jadi angkanya cocok dengan statistik Anki sendiri — termasuk ikut dibatasi
  limit harian. "Tunggakan" ditampilkan terpisah karena daftar deck hanya pernah
  menunjukkan angka yang sudah dibatasi.
- **Efeknya beranimasi terus-menerus.** Di laptop itu sedikit memakan baterai.
  Set `effects: false` untuk mematikannya, dan kalau sistemmu menyalakan
  "reduce motion" efeknya berhenti sendiri.

## Lisensi

MIT untuk kodenya. Art karakter yang kamu tambahkan mengikuti lisensi art itu
sendiri.
