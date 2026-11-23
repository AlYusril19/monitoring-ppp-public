# Panduan untuk AI Agent

Project: bot Telegram monitoring MikroTik (Python, `python-telegram-bot` **13.15** sinkron, data di file JSON).
Baca [`README.md`](README.md) dulu, lalu [`docs/PANDUAN-PENGEMBANGAN.md`](docs/PANDUAN-PENGEMBANGAN.md) sebelum mengubah kode.

## 1. Cari lewat Graphify dulu, baru buka source

1. Graph lokal: `graphify-out/graph.json` → `graphify query "<pertanyaan>"` / `graphify path "<A>" "<B>"`.
2. Graph cloud (MCP Graphify): repo `AlYusril19/monitoring-ppp-public`, branch `master` — hanya mutakhir setelah `git push`.
3. Buka source hanya untuk file yang dirujuk graph atau yang akan diubah.
4. Graph belum ada / usang → pakai pencarian kode biasa; minta izin sebelum membangun graph (Graphify menulis `graphify-out/`).

Query siap pakai per area: [`docs/GRAPHIFY.md`](docs/GRAPHIFY.md). Daftar fungsi lengkap: [`docs/REFERENSI-MODUL.md`](docs/REFERENSI-MODUL.md).

## 2. Titik masuk

| Kebutuhan | Mulai dari |
|---|---|
| Command `/xxx` | `main.py` → dict `COMMANDS` |
| Tombol inline | `handlers/handler_menu.py::menu_callback` (router berdasarkan prefix `callback_data`) |
| Teks bebas / isian form | `handlers/handler_input.py::handle_input` (tuple `WIZARDS`) |
| Foto (bukti transfer / QRIS) | `handlers/handler_wallet.py::capture_payment_proof` |
| Monitoring otomatis | `handlers/check_client_status_and_notify.py` (job tiap 60 detik) |
| Penghapusan chat otomatis | `configs/chat_tracker.py` (group -1 / 1 di `main.py`) |
| Potong saldo | `configs/billing.py::charge_user` — **satu-satunya** jalur |
| Semua pengaturan admin | `configs/app_settings.py` (nilai & default) + `handlers/handler_admin_settings.py` (tombol & command) |
| Hak akses tombol / command admin | `configs/access.py` (`callback_allowed`, `staff_only`) |
| Hapus akun & refund | `handlers/handler_refund.py` |

## 3. Aturan wajib saat mengubah kode

**Data & uang**
- Potong saldo hanya lewat `charge_user()`; jangan mengurangi `saldo` langsung.
- **Jangan menyimpan snapshot data lama.** Pola `users = load_user_data()` → panggil fungsi lain yang ikut menyimpan (`charge_user`, `add_transaction`) → `save_user_data(users)` menimpa perubahan fungsi itu. Simpan dulu, baru panggil; atau muat ulang. (Bug ini pernah membuat biaya notifikasi tidak terpotong.)
- Scheduler menulis hanya lewat `_save_monitoring_state()` / `_save_state_flags()`.
- **Kerja lambat (koneksi router, unduh grafik) lewat `chat_tracker.in_background(...)`**, jangan di thread dispatcher. Load → modify → save di luar update (tugas latar belakang, job) wajib di dalam `with DATA_LOCK:`.
- Field JSON baru: beri default aman untuk data lama (`record.get(key, default)`) dan catat di `docs/DATA.md`.

**Pengaturan & peran**
- **Tidak ada nilai operasional hard-code.** Harga, batas, nominal, profile → `DEFAULT_SETTINGS` + getter/setter di `app_settings.py`, lalu `ADMIN_INPUTS` di `handler_admin_settings.py`.
- Cek peran lewat `is_staff()` / `is_superadmin()`; daftar staf lewat `staff_ids()`.
- Batas server selalu lewat `get_server_limit(user_id)` (titik untuk paket layanan berbayar nanti).

**Telegram & tampilan**
- **Satu fitur = satu implementasi.** Command membuka menu tombol yang sama (`handler_command_redirect.py`, `QueryFromMessage`); jangan menulis logika kedua.
- Kirim pesan lewat `context.bot` / `reply_text` / `send_message(bot, …)` — **bukan** `Bot(...)` baru — agar tercatat `chat_tracker`.
- Balasan otomatis bersifat sementara. Hasil monitoring yang harus tetap dibungkus `with keep_messages():`.
- Form baru: `handle_xxx_input(update, context) -> bool`, daftarkan di `WIZARDS`, dan key status-nya di `PENDING_INPUT_KEYS` (`configs/navigation.py`) agar `/cancel` & ✖️ Batal menutupnya.
- Setiap pesan akhir punya tombol navigasi; setiap form punya ✖️ Batal (tabel di `docs/ALUR-FITUR.md`).
- Teks dinamis (nama PPPoE/server/interface/username) di pesan Markdown wajib `escape_md()`.
- Daftar yang bisa sangat panjang → `send_down_report()`; teks > 4096 karakter otomatis dipecah `TrackingBot`.
- **Jangan membalas chat biasa** (teks tanpa form) dan jangan memakai `quote=True` / `ForceReply`.
- Prefix `callback_data` baru → cabang di `menu_callback` + baris di `docs/ALUR-FITUR.md` §2. Ingat batas 64 byte.

**Versi & rilis**
- **Jangan mengubah `APP_VERSION`/`RELEASED` di `.env`** kecuali pemilik project menyatakan rilis.
- Catat perubahan di `CHANGELOG.md` dan di atas `USER_UPDATES` (yang dilihat user) / `ADMIN_UPDATES` (admin & backend) di `handlers/handler_version.py`; entri di atas `APP_VERSION` otomatis tersembunyi dari user.

**Keamanan**
- Repo GitHub **publik**: jangan commit `.env`, `datauser.json`, `app_info.json`, `chat_messages.json`, `datauser.backup-*.json`, `graphify-out/`.

## 4. Sebelum selesai

1. `python tests/run_regresi.py` → harus `SEMUA LULUS`; tambahkan skenario untuk fitur baru di `tests/regresi.py`.
2. Fungsi baru punya docstring satu baris → `python tools/buat_referensi.py`.
3. Perbarui dokumen terdampak (`docs/*.md`), `CHANGELOG.md`, dan `handler_version.py`.
4. Perubahan struktur → `graphify . --update` (bila diizinkan pemilik).
5. Temuan bug/utang teknis → `docs/CATATAN-TEKNIS.md`.
