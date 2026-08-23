### Amadeus Deck

- **theme** — `"vhs"` (pita video, merah/cyan) atau `"holo"` (hologram, cyan/magenta)
- **daily_target** — target review harian. Dia ikut senang kalau tercapai.
- **effects** — `false` untuk mematikan noise dan garis tracking (hemat baterai)
- **chatter_seconds** — jeda sebelum dia ngomong sendiri saat didiamkan
- **panel_width** — lebar panel karakter, dalam pixel
- **panel_height** — tinggi panel karakter. Dia menempel di kiri bawah,
  jadi angka kecil bikin dia jadi kotak, bukan strip setinggi layar.
- **deck_scroll** — `false` kalau kamu mau daftar deck memanjang ke bawah saja,
  tanpa dibatasi tinggi dan tanpa scroll di dalam kotaknya
- **show_history** — grafik batang review beberapa hari terakhir, di panel kanan
- **show_note** — catatan harian di panel kanan. Tersimpan per tanggal di
  `notes.json` dalam folder addon ini.
- **history_days** — berapa hari yang ditampilkan di grafik
- **right_width** — lebar panel kanan
- **show_stats** — kartu ringkasan di bawah frame karakter
- **deck_max_height** — tinggi maksimum kotak deck. Kalau decknya lebih banyak
  dari itu, kotaknya jadi bisa di-scroll, bukan memanjang ke bawah.
- **theme_bars** — ikut menata bar tombol bawah (Study Now, Create Deck) dan
  toolbar atas supaya sewarna dengan temanya
- **hide_bottom_bar** — `true` kalau kamu mau bar tombol bawah hilang sama sekali.
  Deck tetap bisa diklik langsung, jadi tombol Study Now sebenarnya tidak wajib.
- **theme_deck_list** — `false` kalau kamu mau daftar deck tetap tampilan asli Anki
- **show_on_deck_list** — `false` untuk menyembunyikan tanpa menghapus addon

Taruh gambarmu di folder `character/` di dalam folder addon ini.
Nama filenya harus diakhiri nama emosi, contoh: `kurisu_happy1.png`.

Emosi yang dipakai: normal, happy, winking, sided_pleasant, sided_thinking,
disappointed, sad, annoyed, pissed, angry, blush, sided_blush, eyes_closed,
sided_worried, sided_surprised, indifferent

### Saat review

- **show_in_reviewer** — tampilkan karakter saat mengerjakan kartu
- **reviewer_size** — lebar potretnya, dalam pixel
- **reviewer_corner** — `"bottom-right"`, `"bottom-left"`, `"top-right"`, `"top-left"`
- **reviewer_always_visible** — `true` (bawaan): dia selalu kelihatan di pojok.
  `false`: hanya muncul sebentar tiap kali kamu menjawab, lalu menghilang.
- **reviewer_hide_seconds** — berapa lama reaksinya bertahan sebelum kembali diam

Kartu dan note type kamu tidak disentuh sama sekali. Karakternya ditempel
di atas kartu dalam Shadow DOM, jadi CSS kartumu tidak bisa memengaruhi dia,
dan CSS-nya tidak bisa memengaruhi kartumu.

### Mengubah dialognya

**`lines`** — kalimat di layar deck. **`reviewer_lines`** — kalimat saat review.
Isinya `"state": ["kalimat 1", "kalimat 2"]`; satu diambil acak tiap kali.

State di layar deck:

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

State saat review: `good`, `easy`, `hard`, `wrong`, `annoyed` (Again 3x),
`pissed` (Again 5x), `poke`, `idle`.

Di kalimat layar deck kamu bisa menyisipkan angka: `{due}` sisa kartu,
`{done}` sudah dikerjakan, `{target}` target harian, `{streak}` hari beruntun.
Contoh: `"Sisa {due}. Baru {done} dari {target}."`

**`moods`** dan **`reviewer_moods`** — ekspresi mana yang dipakai tiap state,
diurut dari pilihan pertama. Nama ekspresinya mengikuti akhiran nama file di
folder `character/`.

Kalau satu state kamu hapus dari config, yang bawaan dipakai lagi. Jadi kamu
bisa mengubah satu saja tanpa menyalin semuanya.

### Suara dan cara dialognya muncul

**`typewriter`** — kalimatnya diketik huruf per huruf, bukan muncul sekaligus.
Klik di tengah kalimat untuk langsung menyelesaikannya (bukan mengganti
kalimatnya).

**`typewriter_speed`** — milidetik per huruf. Kecil = cepat. Bawaan `32`.

**`dialog_sound`** — bunyi bicara 8-bit tiap suku kata. Suaranya dibangkitkan
sendiri, tidak ada berkas audio yang perlu diunduh.

**`dialog_volume`** — `0` sampai `1`. Bawaan `0.16`; ini efek latar, bukan
musik, jadi jangan besar-besar.

**`dialog_pitch`** — nada dasar dalam Hz. Bawaan `440`. Naikkan untuk suara
yang lebih tinggi/imut, turunkan untuk yang lebih berat.

**`dialog_every`** — bunyi setiap berapa huruf. Bawaan `3`. Isi `1` kalau mau
tiap huruf berbunyi, tapi di kalimat panjang itu berubah jadi dengungan.

Bunyinya baru terdengar setelah kamu mengklik sesuatu di jendela itu. Bukan bug
— browser memang menahan audio sampai ada interaksi, dan Anki memakai browser
di dalamnya.
