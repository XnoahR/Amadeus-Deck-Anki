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

**Delapan tema** — `vhs`, `holo`, `amber`, `divergence`, `paper` (satu-satunya
yang terang), `slate`, `sakura`, `mint`. Scanline dan noise bisa dimatikan.
Dialog pengaturannya ikut bertema.

---


**Dialognya diketik huruf per huruf** dengan bunyi bicara 8-bit tiap suku
kata — bunyinya dibangkitkan sendiri, tidak ada berkas audio yang diunduh.
Klik di tengah kalimat untuk langsung menyelesaikannya. Matikan lewat
`typewriter` dan `dialog_sound` di config.

**Ekspresi bisa digambar, bukan ditukar.** Dengan `frame_scan` menyala, frame
dikosongkan sampai tinggal garis rasternya sebentar, lalu ekspresi barunya
dibangun turun di belakang kepala pindai — empat pita terlihat, karena sapuan
yang halus terbaca seperti pudar sedangkan yang kasar terbaca seperti mesin
menggambar garis. `tracking` melengkapinya: sesekali satu pita mendatar tergeser
ke samping dan menyala, seperti pita kaset yang kepalanya meleset.

Keduanya tidak menyentuh mulut dan kedip. Keduanya berganti gambar tiap 90–110
md, lebih cepat dari sapuan mana pun, jadi hanya **pergantian ekspresi** yang
menyapu — dan hanya kalau gambarnya memang berbeda.

Semua yang ditulis di bawah ini **mati secara bawaan**. Pemasangan baru
berperilaku persis seperti sebelum semua ini ada; kamu menyalakan yang kamu mau.

---

## Pilihan: suaranya sendiri, dan model Live2D

Dua tambahan yang perlu berkas **yang kamu taruh sendiri**, dan keduanya mati
sampai kamu menyalakannya. Kalau foldernya kosong, menyalakannya tidak mengubah
apa pun: bunyi 8-bit dan gambar PNG tetap dipakai.

### Rekaman suara

Taruh audio di `user_files/voice/` dan dia bicara, bukan berbunyi bip.

Ada dua jenis. **Klip kalimat** dinamai menurut kalimatnya sendiri — sepuluh
karakter pertama SHA-1 dari teks persis di `lines`. Ubah kalimat itu di config
dan tautannya putus sendiri: yang terjadi cuma tidak ada suara untuk kalimat
itu, bukan kalimat yang salah dengan suaranya. **Klip reaksi** didaftar di
`react.json` menurut suasana, karena reaksi menjawab *apa yang dia rasakan*,
bukan *apa yang dia katakan* — "sekali lagi" yang sama cocok untuk setiap
jawaban salah.

```
user_files/voice/
  b44dd8123f.ogg      satu kalimat, dicari lewat teksnya
  react_9f2c1a04bb.ogg
  react.json          {"annoyed": [{"file": "react_9f2c1a04bb.ogg"}], ...}
```

`ogg`, `mp3`, `wav`, dan `m4a` semuanya bisa. Ketika sebuah klip berbunyi, bunyi
8-bit mundur untuk kalimat itu — matikan lewat `voice_clips_hush` kalau mau
dua-duanya.

Panel review menamai keadaannya menurut **apa yang terjadi pada kartu**
(`good`, `wrong`), sementara panel chat menamai wajahnya menurut **apa yang dia
rasakan** (`happy`, `annoyed`). Add-on menerjemahkan keduanya, jadi kartu yang
dijawab sampai ke permukaan mana pun yang sedang menampilkannya dengan wajah dan
klip yang benar-benar ada.

### Model Live2D di panel chat

Taruh model Cubism beserta runtime-nya di `user_files/live2d/`:

```
user_files/live2d/
  lib/live2d.min.js  lib/pixi.min.js  lib/cubism2.min.js
  sesuatu.model.json + apa pun yang dirujuknya
```

Tidak ada yang ikut dipaketkan. Runtime Cubism milik Live2D Inc. dan modelnya
milik siapa pun yang menggambarnya — persis seperti gambar karakter.

Ekspresinya dibangun dari parameter, jadi tidak terbatas pada gambar yang kamu
punya: bukaan mata, arah pandang, tinggi alis, dan mulut. Mulutnya mengikuti
**suara** selama sebuah klip berbunyi — dibaca dari audionya sendiri, bukan
dihitung dari huruf — dan mengikuti ketikan di luar itu. Satu gerak kepala
pendek ikut tiap suasana, ditumpangkan di atas gerak diam bawaan model alih-alih
menggantikannya, dan ekspresinya mengendur kembali ke wajah tenang setelah
beberapa detik.

Kanvasnya baru ditampilkan setelah satu bingkai benar-benar tergambar. WebGL
mati, berkas runtime kurang, model gagal dibaca — semuanya berakhir dengan wajah
PNG masih di tempatnya.

## Pengaturan

**Tools → Amadeus Deck → Pengaturan** berupa formulir, dikelompokkan dalam tab
dan bagian, dan bertema mengikuti sisanya. Semua yang kemungkinan besar ingin
kamu ubah ada di situ, termasuk daftar penyedia AI dengan tombol *tes koneksi*
yang mengirim satu permintaan kecil lalu menampilkan jawabannya apa adanya.

Formulirnya berupa halaman, bukan tumpukan widget, dengan alasan yang spesifik:
begitu stylesheet Qt menyentuh `QCheckBox::indicator`, Qt membuang penggambar
bawaan platform dan tanda centangnya hilang kecuali semua keadaannya digambar
sendiri. Saklar geser tidak punya masalah itu. Kalau halamannya gagal dibangun
karena apa pun, dialog widget lama yang terbuka — pengaturan harus tetap bisa
dijangkau apa pun yang sedang rusak.

**Tools → Add-ons → Amadeus Deck → Config** tetap editor JSON mentah milik Anki,
dan tetap tempat seluruh dialognya, jadi kamu bisa menulis ulang setiap kalimat
dengan suara karaktermu sendiri tanpa menyentuh kode:

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
- **Live2D butuh WebGL di webview Anki.** Di kebanyakan mesin ada, tapi sistem
  yang jatuh ke render perangkat lunak bisa saja tidak. Kalau begitu kanvasnya
  tidak pernah ditampilkan dan wajah PNG tetap dipakai — tidak ada yang perlu
  disetel, tidak ada yang rusak.
- **Suara tidak akan mulai sebelum halamannya diklik sekali.** Peramban menolak
  memutar audio tanpa sentuhan, jadi kalimat pertama setelah panel dibuka bisa
  bisu.
- **Hanya desktop.** AnkiMobile dan AnkiDroid tidak menjalankan add-on Python,
  jadi tidak ada satu pun dari ini yang muncul di sana. Koleksimu tetap sinkron
  seperti biasa.

## Lisensi

MIT untuk kodenya. Apa pun yang kamu tambahkan membawa lisensinya sendiri: art
karakter, rekaman suara, model Live2D, dan runtime Cubism yang dibutuhkan model
itu. Tidak ada satu pun yang ikut dipaketkan, dan folder yang dicarinya dimulai
dalam keadaan kosong.
