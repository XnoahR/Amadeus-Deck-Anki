### Ini pengaturan lengkapnya

Kalau kamu cuma mau ganti tema, mengecilkan suaranya, atau memasang model buat
chat — **jangan di sini.** Pakai formnya:

> **Tools → Amadeus: pengaturan…**

Isinya sama, tapi berupa kotak centang dan angka, bukan JSON, dan tidak bisa
rusak gara-gara koma yang kelewat.

Halaman ini untuk sisanya: kalimat yang dia ucapkan, ekspresi mana untuk state
mana, provider lebih dari satu, dan angka-angka yang jarang disentuh.

Baris `=====  NAMA  =====` cuma penanda kelompok, dan cuma ada di layar ini —
dia tidak ikut tersimpan, jadi tidak perlu kamu jaga. Mau dihapus, digeser, atau
dibiarkan, hasilnya sama.

---

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

**`dialog_mouth`** — mulutnya bergerak selagi dia bicara. Tiga gambar di balik
tiap ekspresi itu posisi mulut (tertutup, sedikit terbuka, terbuka), bukan pose
yang berbeda-beda; frame-nya dijalankan 1-2-3-2-1 dan berhenti di frame 1 waktu
dia diam. Kalau ekspresimu cuma punya satu gambar, dia diam saja.

**`dialog_mouth_ms`** — kecepatan gerakan mulutnya, milidetik per frame.
Bawaan `110`. Kecil = cerewet.

**`dialog_caret`** — kursor kedip di ujung teks selagi dia mengetik, seperti
kursor terminal. Dicabut begitu kalimatnya selesai. Waktu jawabannya masih
mengalir dari model, kursornya tetap berkedip di sela — itu tanda jujur bahwa
masih ada yang datang, bukan hiasan.

**`dialog_caret_char`** — bentuk kursornya. Bawaan `▌`. Bisa diganti `_`, `|`,
`█`, atau apa pun.

**`dialog_every`** — bunyi setiap berapa huruf. Bawaan `3`. Isi `1` kalau mau
tiap huruf berbunyi, tapi di kalimat panjang itu berubah jadi dengungan.

Bunyinya baru terdengar setelah kamu mengklik sesuatu di jendela itu. Bukan bug
— browser memang menahan audio sampai ada interaksi, dan Anki memakai browser
di dalamnya.

**`check_updates`** — cek sekali sehari apakah ada versi baru di GitHub.
Matikan kalau tidak mau add-on ini menghubungi internet sama sekali.

### Chat

Dia bisa diajak bicara: **Tools → Amadeus: buka chat** (atau `Ctrl+Shift+M`).
Jawabannya diketik dengan suara 8-bit yang sama, dan potretnya berganti ikut
nada jawabannya.

**`character_name`** — namanya. Dipakai di judul panel, di menu Tools, dan
menggantikan `{name}` di persona.

**`user_name`** — dia memanggilmu apa. Dikosongkan berarti memakai nama profil
Anki-mu, yang sudah tampil di panel deck; menanyakannya dua kali cuma
merepotkan.

**`persona`** — siapa dia. Ini yang paling berpengaruh. Tulis sebagai perintah,
bukan deskripsi; model menuruti yang pertama dan mengabaikan yang kedua.

**`providers`** — daftar model. Tiap entri: `name`, `kind` (`openai` untuk semua
yang OpenAI-compatible, termasuk OpenRouter; atau `anthropic`), `model`,
`base_url`, dan kuncinya. Kunci boleh ditaruh langsung di `api_key`, atau di
luar config lewat `api_key_env` (nama environment variable), atau
`api_key_file` + `api_key_path` (jalur bertitik ke dalam sebuah file JSON).

Satu field khusus: **`system_in_user`**. Model Gemma di Google menolak system
instruction, padahal persona Amadeus tinggal di sana. Dinyalakan berarti
personanya digabungkan ke pesan pertamamu. Provider Google bawaan sudah
menyalakannya.

**`active_provider`** — nama entri yang dipakai. Bisa juga diganti lewat
dropdown di panelnya.

**`chat_width`** dan **`chat_face_height`** — lebar panel dan tinggi potretnya
dalam piksel. Bawaan `420` dan `220`. Panelnya juga bisa ditarik-tarik seperti
dock biasa; angka ini cuma ukuran saat pertama dibuka.

**`chat_thumb_expression`** — potret kecil di tiap kalimatnya memakai ekspresi
saat kalimat itu diucapkan, jadi waktu menggulung ke atas kamu tetap tahu dia
lagi kesal di titik mana. Dimatikan berarti selalu wajah normal — lebih tenang
kalau ekspresinya sering berganti.

**`chat_thumb_zoom`** dan **`chat_thumb_y`** — krop potret kecilnya, dalam
persen. Bawaannya dipas-kan untuk sprite berdiri seperti Kurisu (wajah di
bagian atas gambar). Kalau karaktermu berbeda bentuk dan yang muncul cuma
rambut atau dada, dua angka inilah yang digeser.

**`about_you`** — hal tetap tentang kamu yang selalu dia tahu: sedang kejar
N2 Desember, benci kanji, maunya dijawab pendek. **Kamu yang menulisnya**, bukan
dia yang menyimpulkan — kesimpulan yang keliru akan terkirim ulang di tiap
percakapan berikutnya selamanya.

**`remember_chat`** — percakapan bertahan setelah Anki ditutup. Tersimpan
sebagai JSON biasa di `user_files/chat.json`: memory yang tidak bisa kamu buka
dan baca adalah memory yang tidak bisa kamu betulkan. Tombol **Lupakan** di
panel chat menghapusnya.

**`remember_messages`** — berapa pesan terakhir yang disimpan. Bawaan `24`.
Ingat, semua yang dia ingat ikut dikirim ke model tiap giliran.

**`send_study_context`** — dia diberi tahu angka belajarmu hari ini: review,
waktu, streak, jatuh tempo, tunggakan, akurasi. Ini yang membuatnya bisa
menyinggung tunggakanmu tanpa ditanya. Matikan kalau tidak mau angka itu
dikirim ke layanan model.

**`send_card_context`** — kalau ada kartu terbuka, isinya ikut dikirim supaya
dia bisa ditanya soal kartu itu.

**`chat_moods`** — ekspresi mana yang dipakai untuk tiap nada jawaban. Dia
diminta membuka balasannya dengan penanda seperti `[happy]`; penandanya
dibuang sebelum ditampilkan.

**`max_history_turns`**, **`max_tokens`**, **`timeout_seconds`** — batas
percakapan dan permintaan.

**Satu wajah, bukan dua.** Kalau panel chat sedang terbuka waktu kamu review,
reaksinya muncul di panel itu dan overlay melayangnya menyingkir. Tutup
panelnya, overlay-nya kembali. Kamu tidak akan pernah melihat dia dua kali di
layar yang sama.
