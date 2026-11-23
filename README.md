# Bot Monitoring SkyTama

Bot Telegram untuk memantau router **MikroTik** milik pelanggan:

- cek pelanggan **PPPoE yang down** (manual atau otomatis terjadwal),
- **grafik traffic** interface dari *Tools > Graphing*,
- **notifikasi otomatis 2 tahap** (⚠️ / 🚨),
- **saldo prabayar**: setiap fitur memotong saldo; topup lewat QRIS + approval admin.

| | |
|---|---|
| **Versi** | 2.3.0 (rilis 23/11/2026). Riwayat: [`CHANGELOG.md`](CHANGELOG.md) |
| **Bahasa** | Python 3.8+ · `python-telegram-bot` **13.15** (API sinkron) · `librouteros` |
| **Penyimpanan** | File JSON lokal, tanpa database |
| **Repo** | `github.com/AlYusril19/monitoring-ppp-public` (**publik** — jangan commit `.env` & file data) |

---

## Peta dokumentasi

| Saya ingin… | Buka |
|---|---|
| Menjalankan bot | [Menjalankan](#menjalankan) di bawah |
| Paham struktur kode, alur update Telegram, scheduler | [`docs/ARSITEKTUR.md`](docs/ARSITEKTUR.md) |
| Daftar command, tombol (`callback_data`), alur tiap fitur | [`docs/ALUR-FITUR.md`](docs/ALUR-FITUR.md) |
| Isi `datauser.json`, `app_info.json`, `chat_messages.json` | [`docs/DATA.md`](docs/DATA.md) |
| **Menambah / mengubah fitur** (resep langkah demi langkah, rilis, uji) | [`docs/PANDUAN-PENGEMBANGAN.md`](docs/PANDUAN-PENGEMBANGAN.md) |
| Daftar semua fungsi per file | [`docs/REFERENSI-MODUL.md`](docs/REFERENSI-MODUL.md) (dibuat otomatis) |
| Bertanya ke Graphify sebelum membaca kode | [`docs/GRAPHIFY.md`](docs/GRAPHIFY.md) |
| Hal yang masih terbuka / utang teknis | [`docs/CATATAN-TEKNIS.md`](docs/CATATAN-TEKNIS.md) |
| Aturan kerja untuk AI agent (Claude, Codex, …) | [`AGENTS.md`](AGENTS.md) |

---

## Menjalankan

```powershell
pip install -r requirements.txt
python main.py
```

Salin [`.env_example`](.env_example) menjadi `.env` di root project, lalu ganti nilai dummy-nya:

```powershell
copy .env_example .env
```

| Variabel | Contoh | Fungsi |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | `123:ABC…` | Token bot utama (dipakai user) |
| `TELEGRAM_BOT_LOG_TOKEN` | `456:DEF…` | Token bot kedua, khusus mengirim log aktivitas |
| `LOG_USER_ID` | `987654321` | Chat ID penerima log (admin/grup log) |
| `ALLOWED_ADMIN_IDS` | `111,222` | ID Telegram **superadmin**, dipisah koma |
| `APP_VERSION` | `2.3.0 (…)` | Versi yang dirilis; dipakai `/version` & pesan startup |
| `APP_NAME` | `bot skytama` | Nama di pesan startup & `/info` |
| `RELEASED` | `22/11/2026` | Tanggal rilis di `/version` |
| `EMAIL` | `dev@…` | Kontak developer di `/version` |

File data (`datauser.json`, `app_info.json`, `chat_messages.json`) dibuat otomatis dan sudah ada di `.gitignore`. Semua pengaturan operasional (harga, batas server, QRIS, role, dsb.) diatur **lewat Telegram** oleh superadmin dan punya nilai default, jadi bot langsung jalan walau database kosong.

### Uji sebelum commit

```powershell
python tests\run_regresi.py
```

Menjalankan 19 skenario (registrasi, server, PPPoE, monitoring 2 tahap, topup, info, chat ringkas, …) dengan Telegram & RouterOS tiruan di folder sementara. Tidak butuh token/internet dan **tidak menyentuh data asli**. Lihat [`docs/PANDUAN-PENGEMBANGAN.md` §7](docs/PANDUAN-PENGEMBANGAN.md#7-uji-regresi).

---

## Struktur folder

```text
main.py                  Entry point: daftar command (COMMANDS), router tombol, scheduler
configs/                 Lapisan layanan: data JSON, pengaturan admin, billing, Telegram, MikroTik
handlers/                Lapisan Telegram: satu file per fitur/menu
models/userdata.py       Sesi router aktif per user (memori)
tests/                   Uji regresi + Telegram/RouterOS tiruan
tools/                   Skrip bantu (buat_referensi.py, skrip rapikan sekali jalan)
docs/                    Dokumentasi pengembangan
graphify-out/            Graph Graphify lokal (artefak, tidak di-commit)
```

Detail tiap file: [`docs/ARSITEKTUR.md` §3](docs/ARSITEKTUR.md#3-peta-file) dan [`docs/REFERENSI-MODUL.md`](docs/REFERENSI-MODUL.md).

---

## Fitur

**User**
- Dashboard tombol: 🖥 Server Saya · 🔧 Server Custom · 📡 Monitor PPPoE · 📈 Monitor Traffic · 💳 Saldo · ⚙️ Monitoring · ℹ️ Info · 🔔 Info Notify · 🧹 Chat · 🗑 Hapus Akun.
- Registrasi ber-antrian (disetujui admin, dengan/tanpa saldo trial).
- Server Saya (maks. sesuai batas admin, default 5) dan Server Custom sementara; password dihapus dari chat.
- Cek PPPoE manual: selalu menampilkan semua nama yang down (daftar panjang → lampiran `.txt`).
- Monitoring otomatis 2 tahap dengan ambang, interval, jeda alert, dan profile pengecualian sendiri.
- Saldo: topup QRIS + bukti transfer, riwayat bulanan/tahunan, rincian biaya di tombol 💸 Biaya.
- Chat selalu ringkas: balasan bot terhapus otomatis, hasil monitoring tetap sebagai log; tombol 🗑 Bersihkan.

**Admin** (superadmin/admin/operator)
- Antrian registrasi & topup, tambah saldo manual (tercatat di log admin).
- 👥 Data User: aktif, arsip, saldo, arsipkan/aktifkan.
- ⚙️ Harga & Role (superadmin): harga, saldo trial, batas server, nominal topup, profile global, role, QRIS.
- Laporan pendapatan bulanan/tahunan; 🧪 User Testing (dashboard user asli).
