# Changelog

Urutan: versi terbaru di atas. Format: **Ditambah / Diubah / Diperbaiki / Dihapus**.
Catatan yang dilihat user di `/version` dikelola terpisah di `handlers/handler_version.py` (`USER_UPDATES` / `ADMIN_UPDATES`).

## 2.3.0 — 23/11/2026 · Paket QRIS, Refund, Keamanan & Performa

Tema: pengaturan admin terpusat, notifikasi 2 tahap, chat ringkas, perapihan kode & dokumentasi.

### Ditambah
**User**
- Alamat router boleh **hostname/DDNS** dan **port API custom** (`router.ddns.net:8000`).
- Koneksi gagal → bot **ping** router: membalas = IP benar, masalah di port/API/NAT/firewall; tidak membalas = router mati / internet putus / IP salah. Login salah = IP & port benar.
- 📈 Traffic: 🌐 **Port Web** per server (⚙️ Kelola) bila service www bukan port 80; grafik gagal menampilkan penyebab + 🌐 Atur Port Web / 🔁 Coba Lagi; Tools > Graphing kosong menampilkan panduan konfigurasi.
- 💳 Saldo: paket nominal dengan QRIS statik masing-masing, plus ✍️ **Nominal Lain** (ketik nominal sendiri, bayar dengan QRIS umum).
- 🗑 Hapus Akun menampilkan **pemberitahuan refund** (saldo, bagian trial, % kebijakan, nominal refund) dan pemberitahuan saat refund dibayar.
- 🌙 **Jam Senyap** di ⚙️ Monitoring (format 24 jam, mis. `22:00-06:00`): tanpa cek, notifikasi, dan potongan saldo selama jam itu.
- Registrasi memakai tombol 📱 **Kirim Nomor Saya** (nomor diverifikasi Telegram).
- Notifikasi otomatis 2 tahap: ⚠️ Tahap 1 memicu notifikasi (berbayar), 🚨 Tahap 2 eskalasi (gratis selama jeda alert); pengingat berbayar bila masih down setelah jeda.
- Riwayat transaksi 📜 bulanan/tahunan di menu Saldo.
- `/cancel` dan tombol ✖️ Batal untuk semua form.
- Tombol 💸 Biaya berisi rincian biaya (kapan dipotong, apa yang gratis); tombol 🆕 Versi.
- Tombol 🗑 Bersihkan semua chat di menu 🧹 Chat.
- Peringatan sekali saat monitoring tidak dapat terhubung ke router, dan saat terhubung lagi.

**Admin**
- 💳 **Paket & QRIS**: tambah paket (nominal → foto QRIS), lihat/ganti QRIS, ubah nominal, hapus paket; QRIS nominal bebas & batas min–max.
- 💸 **Refund**: persentase refund diatur admin; 🗑 Hapus User (superadmin) dengan rincian refund; 💸 Antrian Refund (✅ Sudah Dibayar / ❌ Batalkan).
- 🎁 **Trial & Registrasi** di 👥 Data User: nominal trial, mode (manual / otomatis / nonaktif), batas pengajuan per jam, jeda setelah ditolak.
- **Anti registrasi massal**: nomor wajib kontak Telegram milik akun sendiri; satu trial per nomor & per akun (tercatat permanen di `trial_registry`); nomor yang dipakai akun lain ditandai ⚠️ tanpa trial.
- **Keamanan akses**: pengecekan terpusat `configs/access.py` untuk tombol staf (`admin:`, `users:`, `reg:`, `topup:`, `refund:`) dan command admin; akun belum terdaftar tidak bisa membuka menu user; percobaan akses dicatat ke chat log.
- ⚙️ Harga & Role berbasis tombol: harga, saldo trial, **batas server per user (default 5)**, nominal topup, profile PPPoE global, role. Command baru `/setmaxserver`.
- 👥 Data User: aktif, arsip, saldo, arsipkan/aktifkan lewat tombol.
- Topup & saldo manual menampilkan nama + ID user; saldo manual dikirim ke chat log admin beserta nama admin.

**Pengembangan**
- Uji regresi `python tests/run_regresi.py` (83 skenario, Telegram & RouterOS tiruan, berjalan di folder sementara).
- `tools/buat_referensi.py` → `docs/REFERENSI-MODUL.md`; docstring di semua fungsi.
- `docs/PANDUAN-PENGEMBANGAN.md` (resep fitur, rilis, uji, pemecahan masalah).

### Diubah
- ⚙️ Monitoring: setelah mengisi ambang, profile, atau jam senyap, ringkasan pengaturan terbaru langsung ditampilkan (tidak perlu membuka menu lagi).
- `topup_amounts` diganti `topup_packages` (data lama terbaca otomatis). Tombol 💳 QRIS di dashboard admin menjadi 💳 Paket & QRIS; 🎁 Saldo Trial pindah ke 👥 Data User → 🎁 Trial & Registrasi.
- `/settings` kini khusus staf.
- Topup yang menunggu otomatis dibatalkan saat akun dihapus.
- **"Batas Notif" dihapus**; pemicu notifikasi kini ⚠️ Tahap 1. Router dicek di interval normal selama alert agar eskalasi terdeteksi.
- Cek PPPoE manual selalu menampilkan semua nama yang down; hasilnya 1 pesan log (server, waktu, hasil, label, biaya). Grafik traffic 1 foto dengan keterangan.
- Notifikasi otomatis 1 pesan per kejadian; daftar panjang dikirim sebagai lampiran `.txt`.
- Chat ringkas: balasan bot & ketikan user dihapus saat aksi berikutnya; hasil monitoring, notifikasi, dan pesan dari admin tetap sebagai log (`configs/chat_tracker.py`).
- `/info` & `/version` dibedakan untuk user dan admin; update yang belum dirilis tersembunyi dari user.
- Tombol navigasi di setiap alur (✖️ Batal, ⬅️ Kembali, 🏠 Dashboard, 💳 Isi Saldo).
- Command lama (`/addserver`, `/editserver`, `/delserver`, `/listserver`, `/connect`, `/daftar`, `/topup`) membuka menu tombol yang sama.
- Profile `expired`/`pribadi-home` menjadi profile global yang diatur admin (default sama); user hanya menambah.
- Nominal topup dari pengaturan admin; QRIS tampil setelah memilih nominal bersama instruksi.
- Traffic: grafik diambil dulu, saldo dipotong hanya bila berhasil.
- Waktu topup dicatat dalam WIB.

### Diperbaiki
- **Bot lambat / kurang responsif**: bot kini memakai connection pool 16 koneksi (sebelumnya 1 koneksi yang dipakai long-polling, sehingga tiap balasan membuka koneksi TLS baru). Penghapusan pesan lama dan log admin berjalan di latar belakang, tidak lagi menunda balasan.
- Cek PPPoE, traffic, daftar interface, dan uji koneksi form server berjalan di latar belakang: router yang lambat/timeout tidak lagi membuat bot macet untuk user lain.
- Monitoring otomatis mengecek user secara paralel; router yang timeout tidak menunda user lain.
- Data aman di banyak thread: `DATA_LOCK` + penulisan file atomik (file setengah tertulis tidak lagi terbaca sebagai data kosong). ⏸ Jeda saat pengecekan berjalan tidak lagi tertimpa job.
- **Pesan koneksi router yang jelas**: tidak ada lagi "Terjadi kesalahan: timed out". Login salah, router tidak merespons, API mati, alamat salah, atau koneksi putus kini dijelaskan, dan saldo **tidak dipotong**.
- Tambah/edit server & Server Custom kini **menguji koneksi** sebelum disimpan/dipakai; gagal → server belum disimpan (🔁 Isi Ulang / 💾 Simpan Tanpa Cek).
- Router yang putus di tengah cek tidak lagi dianggap "UP semua"/"pulih" dan tidak memotong saldo (`get_down_users` kini melempar `RouterError`).
- Monitoring otomatis: pesan "🚨 Server tidak dapat dihubungi" (sekali) + "kembali terhubung sejak …", dicatat di chat log.
- **Biaya notifikasi otomatis tidak pernah terpotong** (tertimpa snapshot scheduler) — kini terpotong & tercatat; tidak terpotong ganda bila pesan gagal.
- Ganti `APP_VERSION` tidak lagi menghapus pengaturan & antrian di `app_info.json`.
- User arsip tidak lagi dipantau, dipotong biaya, atau dikirimi pesan startup.
- Nama berisi `_` atau `*` tidak lagi menggagalkan pesan (`escape_md`).
- "Message is too long" pada daftar down yang panjang.
- Bot tidak lagi auto-reply: tanpa quote, tanpa balasan tumpukan pesan lama saat start, teks bebas tidak dibalas; bar "Reply to bot" peninggalan form lama ditutup otomatis.
- Dashboard User Testing identik dengan dashboard user dan tidak keluar sendiri.
- Hapus server saat Server Custom aktif tidak lagi error; `/historybulanan` tanpa transaksi tidak error; label bulan laporan admin benar.
- Admin/operator dapat memakai `/useraktif`, `/userarsip`, `/aktifkan`, `/arsipkan`, `/saldouser`, `/testppp`, `/traffic`.
- Pesan startup tetap berjalan meski ada user yang memblokir bot.
- `.gitignore` memuat `.env`, `graphify-out/`, `chat_messages.json`, backup data.

### Dihapus
- Handler lama: `handler_list_server`, `handler_connect_server`, `handler_daftar`, `handler_saldo_topup`, `handler_saldo_user`, `handler_exit_interface`; `fix_datauser.py`; `Read.me`.
- `last_notification_time.json` (tidak pernah dibaca), `send_image`, `get_interfaces`, alur login lama lewat teks bebas, `ConversationHandler` `/connect`.

## 2.2.1 — 22/11/2026 · Monitoring Threshold & Server Management

**Ditambah**
- User dapat mengatur minimal jumlah pelanggan down sebelum notifikasi dikirim (`notify_down_threshold`).
- User dapat mengatur ambang Warning ⚠️ (`warning_threshold`) dan Warning 🚨 (`critical_threshold`).
- User dapat mengecualikan profile PPPoE sendiri; `expired` dan `pribadi-home` tetap selalu dikecualikan.
- Tombol **Kelola** di *Server Saya* untuk edit atau hapus server (dengan konfirmasi).

**Diubah**
- Teks `/why`, `/infonotify`, `/biaya`, `/info`, `/version` diperbarui.
- Dokumentasi arsitektur dan panduan Graphify diperbarui.

## 2.2.0 — 21/11/2026 · Dashboard & Saldo

**Ditambah**
- Dashboard tombol terpisah untuk user, admin, dan *User Testing*.
- Registrasi mandiri ber-antrian; admin memilih **Setujui + Trial**, **Tanpa Trial**, atau **Tolak**.
- Hapus akun oleh user.
- Topup via QRIS + bukti transfer, antrian approval topup, saldo manual oleh staf.
- Laporan pendapatan bulanan/tahunan di Dashboard Admin (saldo trial tidak dihitung sebagai pendapatan).
- Server Custom sementara (tidak disimpan ke daftar server).
- Interval monitoring normal/alert yang dapat diatur per user.
- Role `admin` dan `operator`; harga fitur dan saldo trial diatur lewat Telegram.

**Diubah**
- Traffic mengikuti *Tools > Graphing*; entry `all` aktif menampilkan seluruh interface. Daftar interface menampilkan komentar RouterOS.
- Monitor PPPoE mengarahkan ke pemilihan server bila router belum terhubung.
- Antrian registrasi dan topup disimpan di `app_info.json` agar tidak hilang.

## 2.1.2 — 10/04/2025
- **Diubah:** batas server per user dari 2 menjadi 4 *(per 2.2.x batas ini tidak lagi ditegakkan di kode — lihat `docs/CATATAN-TEKNIS.md`)*; harga diperbarui.
- **Ditambah:** manajemen user aktif/arsip (`/arsipkan`, `/aktifkan`, `/useraktif`, `/userarsip`); info untuk admin.

## 2.1.1 — 22/06/2024
- **Ditambah:** `created_at`/`updated_at` di setiap record, `/editserver`, pesan startup, utilitas `get_current_time`.

## 2.1.0 — 10/06/2024 · Notify
- **Ditambah:** riwayat transaksi (`handler_transaction`, `handler_all_transaction`), `add_transaction`, `calculate_transaction`.
- **Ditambah:** `check_client_status_and_notify` dijalankan otomatis (awalnya tiap 30 menit), `last_notification_time.json`.
- **Diubah:** beberapa `send_message` tidak lagi bergantung pada `update`/`context`.

## 2.0.1
- **Diubah:** handler server menyimpan ke JSON (maks. 2 server).
- **Ditambah:** `/listserver`, `/addserver`, `/delserver`, `/connect`, fitur custom IP.

## 2.0.0 · Saldo
- **Ditambah:** topup, saldo user, saldo, daftar, biaya; `configs/data_json_user.py`, `configs/format_rupiah.py`.
- **Dihapus:** `allowed_user_ids` (diganti pengguna terdaftar di JSON).

## 1.5.1
- **Ditambah:** monitoring traffic (server LB Home).

## 1.4.3
- **Diperbaiki:** pesan LOG, pesan user, dan pesan warning di `handler_start`.

## 1.4.2
- **Ditambah:** LOG aktivitas user (variabel `.env`, `send_message`, `handler_start`).

## 1.4.1
- **Ditambah:** fitur jam down (`mikrotik_function`, `handler_start`).
