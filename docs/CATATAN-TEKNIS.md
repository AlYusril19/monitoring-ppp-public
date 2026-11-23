# Catatan Teknis & Utang Teknis

Daftar hal yang **masih terbuka**, diurutkan dari yang paling berisiko. Centang dan pindahkan ke bagian "Selesai" saat diperbaiki, lalu catat di `CHANGELOG.md`.

## Terbuka

### Keamanan & data
- [ ] **Password router tersimpan plain text** di `datauser.json`. Usulan: enkripsi dengan `cryptography.Fernet`, kunci di `.env` (`SERVER_SECRET_KEY`); enkripsi di `handle_server_wizard`, dekripsi di `_connect_server`, `_show_interfaces`, `_run_traffic`, dan scheduler. Butuh migrasi data lama.
- [ ] **Penulisan JSON tidak atomik.** Bot & scheduler bisa menulis file yang sama bersamaan. Usulan: tulis ke file sementara lalu `os.replace`, plus `threading.Lock` di `data_json_user.py`.
- [ ] Bila `.env` pernah ter-commit ke repo publik: keluarkan dari git (`git rm --cached .env`) dan **ganti token bot** di @BotFather.

### Fitur & perilaku
- [ ] **Paket layanan berbayar** (rencana pemilik). Hook siap: `app_settings.get_server_limit(user_id)`; resep di `PANDUAN-PENGEMBANGAN.md` §3.8.
- [ ] **User arsip masih bisa memakai fitur manual** (PPPoE, traffic, topup). Arsip saat ini hanya menghentikan monitoring otomatis & pesan startup.
- [ ] **User Testing tidak memotong saldo** (staf gratis), sehingga alur saldo habis hanya bisa diuji dengan akun non-staf atau `tests/regresi.py`.
- [ ] `callback_data` maksimal 64 byte: nama interface yang sangat panjang di `tr:iface:<srv>:<iface>` bisa ditolak Telegram. Usulan: kirim index interface.
- [ ] Pesan yang terkirim > 48 jam lalu atau sebelum `chat_tracker` aktif tidak bisa dihapus bot (batas Telegram).
- [ ] **Riwayat transaksi ikut terhapus saat akun dihapus**, sehingga laporan pendapatan bulan lalu bisa berkurang. Jejak yang tersisa: chat log admin + `app_info.refund_requests`. Usulan: arsipkan `transactions` ke `app_info.deleted_accounts`.
- [ ] Refund dihitung konservatif: saldo dikurangi **seluruh** trial yang pernah diterima (trial dianggap terpakai terakhir). Bila kebijakan berubah (mis. trial dipakai lebih dulu), ubah `handler_refund.refund_quote`.
- [ ] Registrasi dengan nomor yang sudah dipakai akun lain tetap boleh (tanpa trial, ditandai ⚠️ untuk admin). Bila ingin ditolak total, tambahkan cek di `handle_contact`.
- [ ] Pengajuan registrasi lama (sebelum 2.3.0) tidak punya `phone_verified`; ditampilkan "diketik manual" di antrian.

### Kode
- [ ] Diagnosa ping (`mikrotik_function.ping_host`) memakai program `ping` sistem. Di server/Docker tanpa `ping` (paket `iputils-ping`) diagnosa dilewati diam-diam. Ping menambah ±2–6 detik pada pesan gagal koneksi (monitoring: hanya saat pesan pertama).
- [ ] Batas pengajuan per jam dihitung dari `registration_requests` yang terus bertambah. Usulan: bersihkan pengajuan > 90 hari.
- [ ] `handlers/handler_menu.py` masih besar (±25 KB). Usulan: pecah menjadi `menu_server.py`, `menu_traffic.py`, `menu_admin.py` dengan `menu_callback` tetap sebagai router.
- [ ] `handler_start.py` / `handler_traffic.py` bernama historis (isinya PPPoE & traffic). Ganti nama bila sempat (perbarui impor & dokumen).
- [ ] Uji regresi belum mencakup `fetch_image` (unduhan grafik) dan koneksi Telegram/RouterOS sungguhan.

## Selesai (2.3.0)

Ringkas; rincian di `CHANGELOG.md`.
- Biaya notifikasi otomatis tidak terpotong (snapshot scheduler menimpa `charge_user`).
- `app_info.json` terhapus saat `APP_VERSION` berubah.
- User arsip tetap dipantau & dipotong.
- Batas server tidak ditegakkan / hard-code; profile, nominal topup, harga ditulis di banyak tempat → satu sumber `app_settings.py`.
- Command lama dengan logika ganda → membuka menu tombol yang sama.
- `/cancel` hanya berlaku di `/connect`; Markdown gagal karena `_`/`*`; "Message is too long".
- Auto-reply (quote, tumpukan pesan saat start, teks bebas), bar "Reply to" dari `ForceReply`.
- Chat penuh balasan bot → `chat_tracker` (sementara vs log) + 🗑 Bersihkan.
- Dashboard User Testing berbeda dari user; admin/operator ditolak di menu Data User.
- Kode mati dihapus (6 handler lama, `fix_datauser.py`, `last_notification_time.json`, `send_image`, `get_interfaces`, alur login teks bebas).
