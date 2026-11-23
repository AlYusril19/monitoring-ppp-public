# Panduan Pengembangan

Resep langkah demi langkah untuk mengubah bot tanpa merusak aturan yang sudah ada.
Baca [`ARSITEKTUR.md`](ARSITEKTUR.md) untuk gambaran besar; daftar fungsi di [`REFERENSI-MODUL.md`](REFERENSI-MODUL.md).

---

## 1. Persiapan

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

- **Pakai bot uji terpisah** saat mencoba fitur: buat bot baru di @BotFather dan isi tokennya di `.env` salinan, supaya user sungguhan tidak menerima pesan percobaan.
- Hanya **satu proses bot** boleh berjalan per token. Error `Conflict: terminated by other getUpdates request` berarti ada proses lama yang masih hidup.
- `python-telegram-bot` dikunci di **13.15** (API sinkron). Versi 20+ memakai `async` dan butuh migrasi besar.

## 2. Alur kerja satu perubahan

```text
1. Pahami      graphify query "..."  (docs/GRAPHIFY.md)  atau baca REFERENSI-MODUL.md
2. Ubah        ikuti resep §3 dan aturan §4
3. Uji         python tests\run_regresi.py   → SEMUA LULUS; tambah skenario baru (§7)
4. Coba nyata  jalankan bot uji, coba alurnya di Telegram
5. Dokumentasi docstring fungsi baru → python tools\buat_referensi.py
               docs/*.md terdampak, CHANGELOG.md, handler_version.py (§6)
6. Graph       graphify . --update
7. Commit      git add -A && git commit -m "..." && git push
```

---

## 3. Resep

### 3.1 Menambah tombol di dashboard user

1. Tambahkan tombol di `handlers/handler_menu.py::_user_dashboard_keyboard` (dipakai user **dan** User Testing):
   ```python
   [InlineKeyboardButton("🆕 Fitur Baru", callback_data="menu:fiturbaru")],
   ```
2. Tambahkan cabang di `menu_callback` (sebelum cabang yang memakai `startswith` yang lebih umum):
   ```python
   if data == "menu:fiturbaru":
       query.answer()
       fitur_baru(update, context)        # fungsi di handler baru/lama
       return
   ```
3. Di fungsi tujuan: akhiri setiap pesan dengan tombol navigasi (§4.1). Untuk mengganti isi menu yang ditekan, pakai `query.edit_message_text(...)`; untuk pesan baru, `update.effective_message.reply_text(...)`.
4. Catat `menu:fiturbaru` di `docs/ALUR-FITUR.md` §2.
5. Tombol untuk admin: tambahkan di `_send_admin_dashboard` dengan prefix `admin:` lalu cabang `action == "..."` di `_admin_callback` (sudah dicek `is_staff`).

> `callback_data` maksimal **64 byte**. Untuk data panjang (nama interface, dsb.) kirim index, bukan nama.

### 3.2 Menambah command

1. Buat fungsi `(update, context)` di handler yang sesuai.
2. Daftarkan di `main.py` → dict `COMMANDS`: `"namacommand": fungsi,`.
3. **Bila fitur itu sudah punya tombol**, command cukup membuka menu yang sama (jangan menulis logika kedua):
   ```python
   from configs.navigation import QueryFromMessage
   def fiturbaru_command(update, context):
       buka_menu_fitur(QueryFromMessage(update))   # fungsi yang biasa menerima `query`
   ```
   Contoh nyata: `handlers/handler_command_redirect.py`.
4. Tambahkan ke tabel `docs/ALUR-FITUR.md` §1 dan ke daftar command di `handler_info.py` (user/admin).

### 3.3 Menambah form isian (wizard)

Form = bot bertanya, user mengetik jawaban.

1. **Buka form** (dari tombol): simpan status di `context.user_data`, tampilkan prompt dengan ✖️ Batal:
   ```python
   from configs.navigation import cancel_keyboard
   def mulai_form(query, context):
       context.user_data["fiturbaru_step"] = "nama"
       query.answer()
       query.edit_message_text("Masukkan nama:", reply_markup=cancel_keyboard())
   ```
2. **Tangani jawaban**: fungsi yang mengembalikan `True` bila pesan dipakai:
   ```python
   def handle_fiturbaru_input(update, context):
       step = context.user_data.get("fiturbaru_step")
       if not step:
           return False
       value = update.effective_message.text.strip()
       if not value:
           update.effective_message.reply_text("Tidak boleh kosong.", reply_markup=cancel_keyboard())
           return True                      # tetap dipakai: form masih terbuka
       context.user_data.pop("fiturbaru_step", None)
       ...                                  # simpan
       update.effective_message.reply_text("✅ Tersimpan.", reply_markup=home_keyboard())
       return True
   ```
3. Daftarkan fungsi di `handlers/handler_input.py` → tuple `WIZARDS`.
4. Tambahkan `"fiturbaru_step"` ke `configs/navigation.py` → `PENDING_INPUT_KEYS` (agar `/cancel` & ✖️ Batal menutupnya).
5. Pesan jawaban user otomatis dihapus (`mark_input_consumed` dipanggil `handle_input`). Untuk data sensitif (password), hapus segera: `update.effective_message.delete()`.

### 3.4 Menambah pengaturan admin

Contoh: `max_notif_per_hari` (angka, default 10).

1. `configs/app_settings.py`:
   ```python
   DEFAULT_SETTINGS = { ..., "max_notif_per_hari": 10 }
   # load_settings(): tambahkan key ke tuple int yang dibaca dari app_info.json
   for key in ("trial_balance", "max_servers", "max_notif_per_hari"):
   def get_max_notif_per_hari():
       """Batas notifikasi per hari per user."""
       return int(load_settings()["max_notif_per_hari"])
   def set_max_notif_per_hari(amount):
       """Ubah batas notifikasi per hari."""
       _update_setting("max_notif_per_hari", int(amount))
   ```
2. `handlers/handler_admin_settings.py`:
   - `ADMIN_INPUTS["max_notif"] = ("Masukkan batas notifikasi per hari:", True)` (`True` = hanya superadmin)
   - cabang di `apply_admin_input`: validasi dengan `_parse_amount(value, minimum=1)`, panggil setter, kembalikan teks konfirmasi;
   - tombol di `admin_settings_menu`: `InlineKeyboardButton("🔔 Batas Notif/Hari", callback_data="admin:set:max_notif")`;
   - baris di `settings_text`.
3. (Opsional) command: fungsi `_run_command(update, "max_notif", "Gunakan: /setmaxnotif <jumlah>", context.args or [])` + daftar di `COMMANDS`.
4. Pakai `get_max_notif_per_hari()` di kode — **jangan** menulis angka langsung.
5. Dokumentasi: `ALUR-FITUR.md` §5, `DATA.md` (contoh `settings`), `/info` admin bila perlu.

### 3.5 Menambah fitur berbayar

1. Tambahkan harga: `PRICE_LABELS["fiturbaru"] = "Fitur Baru"` dan `DEFAULT_SETTINGS["prices"]["fiturbaru"] = 100` di `app_settings.py`. Otomatis muncul di `/biaya`, `/settings`, dan bisa diubah via `/setprice fiturbaru <n>`. Tambahkan tombol 💲 di `admin_settings_menu` + key `price:fiturbaru` di `ADMIN_INPUTS` bila perlu tombol.
2. Potong saldo **setelah** proses dipastikan berhasil:
   ```python
   success, cost, remaining = charge_user(user_id, "fiturbaru")
   if not success:
       send_message(bot, chat_id, "Saldo tidak mencukupi.", reply_markup=topup_keyboard())
       return
   ```
3. Jangan memanggil `save_user_data()` dengan data yang dimuat **sebelum** `charge_user` (lihat `AGENTS.md` §3).
4. Jelaskan kapan dipotong di `handler_biaya.user_cost_text`.

### 3.6 Hasil yang harus tetap di chat (log)

Semua balasan otomatis bersifat sementara. Untuk hasil yang perlu disimpan user:
```python
from configs.chat_tracker import keep_messages
with keep_messages():
    send_message(bot, chat_id, teks_hasil)      # atau bot.send_photo / send_down_report
```
Pesan yang dikirim di luar update (job scheduler) otomatis menjadi log. Jangan memberi tombol yang **mengedit** pesan log — `TrackingBot` sudah melindunginya dengan mengirim pesan baru.

### 3.7 Daftar yang bisa sangat panjang

Teks > 4096 karakter otomatis dipecah oleh `TrackingBot`. Untuk daftar pelanggan down pakai `send_down_report(bot, chat_id, header, down_users, footer, reply_markup)` → 1 pesan, atau 1 pesan + lampiran `.txt` bila terlalu panjang.

### 3.8 Paket layanan berbayar (rencana)

Titik masuk sudah ada: `app_settings.get_server_limit(user_id)` dipakai semua pengecekan batas server.
1. Simpan definisi paket di `DEFAULT_SETTINGS["plans"]` (mis. `{"basic": {"max_servers": 2}, "pro": {"max_servers": 10}}`) dan paket user di `datauser[user]["plan"]`.
2. Ubah **hanya** `get_server_limit` untuk membaca paket user (fallback ke `get_max_servers()`).
3. Harga per paket dapat mengikuti pola yang sama di `get_price`.
4. Menu admin untuk memilih paket user: ikuti §3.4 (key baru di `ADMIN_INPUTS`).

### 3.9 Mengubah aturan notifikasi otomatis

Semua di `handlers/check_client_status_and_notify.py`; level dari `app_settings.alert_level()`.
- Simpan state hanya lewat `_save_state_flags()` / `_save_monitoring_state()`.
- Simpan state **sebelum** mengirim pesan (pesan gagal tidak boleh memicu potongan kedua).
- Uji dengan `monitoring_tick()` di `tests/regresi.py`.

---

## 4. Aturan pesan

### 4.1 Tombol navigasi
| Situasi | Pakai |
|---|---|
| Form menunggu ketikan | `cancel_keyboard()` |
| Hasil di sub-menu | `back_keyboard("menu:asal", "⬅️ Label")` |
| Hasil akhir / error | `home_keyboard()` |
| Saldo kurang | `topup_keyboard()` |
| Daftar pilihan | tambahkan `dashboard_row()` di akhir |

### 4.2 Markdown
- `send_message(bot, chat_id, text)` memakai Markdown (legacy). Teks dinamis **wajib** `escape_md()`; nama seperti `pel_01` tanpa escape membuat Telegram menolak pesan (`Can't parse entities`).
- Pesan berisi data mentah (nama, ID) yang tidak perlu format → kirim tanpa `parse_mode`.

### 4.3 Jangan
- `Bot(token=...)` baru untuk mengirim ke user (tidak tercatat `chat_tracker`). Pakai `context.bot`.
- `ForceReply`, `quote=True`, atau membalas teks bebas.
- Mengubah `APP_VERSION` di `.env` tanpa keputusan rilis.

## 5. Peran & keamanan

- Fitur staf: cek `is_staff(user_id)` di awal; fitur superadmin: `is_superadmin(user_id)`.
- Notifikasi ke semua staf: `for staff_id in staff_ids(): ...` (bungkus `try/except`, staf bisa belum membuka bot).
- Password router: hapus pesan user segera setelah dibaca. Enkripsi masih utang teknis.
- Repo publik: periksa `git status` sebelum commit; `.env` dan file `*.json` data tidak boleh ikut.

## 6. Rilis versi

Selama pengembangan:
1. Tambahkan entri di **atas** `USER_UPDATES` (yang dilihat/dipakai user) dan `ADMIN_UPDATES` (fitur admin & perbaikan backend) di `handlers/handler_version.py`, dengan nomor versi yang akan dirilis. Entri di atas `APP_VERSION` tersembunyi dari user, berlabel "belum dirilis" untuk admin.
2. Catat di `CHANGELOG.md` bagian versi yang sedang dikembangkan.
3. Fitur user baru → perbarui `USER_FEATURES`, panduan di `handler_info.user_info_messages`, dan biaya di `handler_biaya`.

Saat rilis (diputuskan pemilik project):
1. `python tests\run_regresi.py` → SEMUA LULUS.
2. Ubah `.env`: `APP_VERSION=2.3.0 (...)`, `RELEASED=dd/mm/yyyy`.
3. Ubah judul versi di `CHANGELOG.md` dari "dalam pengembangan" menjadi tanggal rilis.
4. Restart bot → user menerima "Bot telah diperbarui ke versi …" dan update tampil di `/version`.
5. `git tag v2.3.0 && git push --tags` (opsional).

## 7. Uji regresi

```powershell
python tests\run_regresi.py
```

- Menyalin project ke folder sementara, memakai Telegram & RouterOS tiruan (`tests/stubs/`), lalu menjalankan `tests/regresi.py`. Data asli, `.env`, dan token tidak disentuh.
- Bila `pytz`/`python-dotenv` belum terpasang, cadangan di `tests/stubs_fallback/` dipakai.
- Keluaran: `PASS`/`FAIL` per skenario, kode keluar 1 bila ada yang gagal.

**Menambah skenario** — di akhir `tests/regresi.py`, sebelum ringkasan:
```python
press(USER, "menu:fiturbaru")                      # tekan tombol
say(USER, "isian")                                 # ketik teks / command
check("Tersimpan" in last(USER), "fitur baru menyimpan isian")
```
Alat bantu: `say(uid, text)`, `press(uid, callback_data)`, `send_photo(uid)`, `last(uid)`, `monitoring_tick(down)`, `saldo()`, `ROUTER["down"]`, `ROUTER["fail"]`, `LIVE[uid]` (pesan yang masih tampil). ID: `SUPERADMIN=1`, `USER=42`, `LOG_CHAT=9`.

Tiruan Telegram meniru batas asli (teks 4096, caption 1024) dan menolak hapus pesan yang tidak ada. Bagian yang **tidak** teruji: koneksi Telegram sungguhan, RouterOS sungguhan, dan unduhan grafik (`fetch_image`) — coba manual dengan bot uji.

## 8. Checklist sebelum commit

- [ ] `python tests\run_regresi.py` → SEMUA LULUS (skenario baru ditambahkan)
- [ ] Dicoba di bot uji (alur utama + ✖️ Batal + 🏠 Dashboard)
- [ ] Fungsi baru ber-docstring → `python tools\buat_referensi.py`
- [ ] `docs/*.md` terdampak, `CHANGELOG.md`, `handler_version.py` diperbarui
- [ ] Tidak ada nilai hard-code baru (harga, batas, nominal) → ke `app_settings`
- [ ] `git status` tidak memuat `.env` / `*.json` data
- [ ] `graphify . --update`

## 9. Pemecahan masalah

| Gejala | Penyebab & solusi |
|---|---|
| `Conflict: terminated by other getUpdates request` | Dua proses bot dengan token sama. Matikan proses lama (Task Manager → python). |
| `Can't parse entities` | Teks dinamis tanpa `escape_md()` di pesan Markdown. |
| `Message is too long` | Seharusnya tidak terjadi lagi (dipecah otomatis); bila muncul, pesan dikirim tanpa `TrackingBot` (mis. `Bot(...)` baru). |
| `Message to edit not found` | Pesan sudah dihapus `chat_tracker`. Pastikan alur mengedit `query.message` milik tombol yang ditekan, bukan ID lama. |
| Pesan lama tidak terhapus | Lebih dari 48 jam, atau terkirim sebelum `chat_tracker` aktif. Gunakan Clear history di aplikasi. |
| Bar biru "Reply to …" | Sisa `ForceReply` versi lama; tertutup otomatis sekali per chat (`clear_reply_interface`). |
| Bot diam saat user mengetik | Disengaja bila tidak ada form terbuka. Pastikan form baru terdaftar di `WIZARDS`. |
| Form tidak tertutup oleh /cancel | Key status form belum ada di `PENDING_INPUT_KEYS`. |
| Saldo tidak berkurang | Akun staf memang gratis; atau ada `save_user_data()` dengan data lama setelah `charge_user()`. |
| Monitoring tidak jalan untuk user | `aktif: false` (arsip), `monitoring_state.paused`, belum punya server, atau belum jatuh tempo interval. |
| Interface traffic kosong | Tools > Graphing > Interface belum diaktifkan di router. |
| Gagal login router | RouterOS API (`/ip service` api, port 8728) mati/diblokir, atau akun salah. |
