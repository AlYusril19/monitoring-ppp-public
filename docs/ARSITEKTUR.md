# Arsitektur Bot Monitoring SkyTama

Dokumen ini menjelaskan struktur aplikasi agar perubahan berikutnya dapat dilakukan tanpa menebak alur kode.

## Alur utama

`main.py` mendaftarkan command, callback tombol, wizard input, dan scheduler. Semua input tombol masuk ke `handlers/handler_menu.py`.

| Bagian | Tanggung jawab |
|---|---|
| `handlers/handler_menu.py` | Dashboard user/admin, tombol server, PPPoE, traffic, dan navigasi |
| `handlers/handler_onboarding.py` | Registrasi, trial saldo, hapus akun |
| `handlers/handler_server.py` | Server tersimpan dan wizard tambah server |
| `handlers/handler_start.py` | Tes PPPoE serta server custom sementara |
| `handlers/handler_traffic.py` | Grafik traffic dan pemotongan saldo traffic |
| `handlers/check_client_status_and_notify.py` | Scheduler monitoring berkala dan notifikasi down/pulih |
| `handlers/handler_wallet.py` | QRIS, request saldo, bukti transfer, approval staf |
| `configs/data_json_user.py` | Penyimpanan `datauser.json` dan `app_info.json` |
| `configs/app_settings.py` | Harga, role, saldo trial, QRIS, interval default |
| `configs/billing.py` | Satu jalur pemotongan saldo dan ledger transaksi |

## Data pengguna

`datauser.json` memakai ID Telegram sebagai key. Field penting:

```json
{
  "123456": {
    "username_telegram": "nama_saat_registrasi",
    "saldo": 5000,
    "servers": [],
    "monitoring": {
      "normal_interval_minutes": 20,
      "alert_interval_minutes": 120
    },
    "transactions": []
  }
}
```

Nama pada log memakai `username_telegram` dari database, bukan username Telegram yang sedang aktif.

## Server dan keamanan

`Server Saya` menyimpan kredensial untuk pemakaian ulang. `Server Custom` hanya hidup di memori selama proses bot; server ini tidak masuk `datauser.json`.

Pesan password pada wizard dihapus setelah diterima. Ini hanya melindungi riwayat chat; kredensial server tersimpan masih perlu dienkripsi sebelum bot dipakai di lingkungan produksi.

## Monitoring dan Graphing

Scheduler bangun setiap satu menit lalu memeriksa apakah interval setiap user sudah jatuh tempo. Setelah status down, interval alert yang lebih panjang dipakai. Jika status pulih, interval normal dipakai kembali.

Pilihan interface traffic berasal dari RouterOS `Tools > Graphing > Interface` (`/tool/graphing/interface/print`):

- entry interface spesifik aktif: hanya interface itu yang ditampilkan;
- entry `all` aktif: seluruh interface RouterOS dapat dipilih;
- tidak ada entry aktif: bot tidak menawarkan interface traffic.

Grafik ditampilkan dari endpoint Graphing MikroTik `http://HOST/graphs/iface/INTERFACE/daily.gif`.

## Role

- `superadmin`: harga, saldo trial, QRIS, dan role.
- `admin`: approval topup dan report.
- `operator`: approval topup dan report.
- `user`: monitoring serta saldo sendiri.

Role diatur melalui `/setrole <id> <operator|admin|user>`. Harga melalui `/setprice`, trial melalui `/settrial`, dan QRIS melalui `/setqris` atau Dashboard Admin.
