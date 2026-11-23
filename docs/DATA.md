# Struktur Data

Semua data disimpan sebagai file JSON di root project, dibuat otomatis, dan ada di `.gitignore`.
**Jangan commit file-file ini** (repo GitHub publik).

| File | Isi | Akses lewat |
|---|---|---|
| `datauser.json` | Akun user: saldo, server, pengaturan & state monitoring, transaksi | `configs/data_json_user.py` (`load/save_user_data`) |
| `app_info.json` | Versi, **pengaturan admin**, antrian registrasi & topup, chat yang sudah dibersihkan | `configs/data_json_user.py` (`load/save_app_info`), `configs/app_settings.py` |
| `chat_messages.json` | ID pesan per chat (≤ 47 jam) + mana yang sementara | `configs/chat_tracker.py` |

> Mengosongkan data: hentikan bot, isi `datauser.json` dengan `{}`. Pengaturan admin tetap ada di `app_info.json`; bila file itu juga dikosongkan, semua kembali ke `DEFAULT_SETTINGS`.

## `datauser.json`

Key = ID Telegram (string).

```jsonc
{
  "123456": {
    "user_id": 123456,
    "username_telegram": "nama_saat_registrasi", // dipakai di log & topup, bukan username aktif
    "nohp": "628xxxxxxxxxx",       // sejak 2.3.0 dinormalisasi 62..., dari kontak Telegram
    "phone_verified": true,        // nomor dibagikan lewat tombol kontak (data lama: tidak ada = false)
    "saldo": 5000,
    "aktif": true,                 // false = arsip: tidak dipantau otomatis, tidak dikirimi pesan startup
    "account_type": "client",      // "client" | "admin" (migrate_account_types / set_role)
    "created_at": "2026-11-22 13:49:06",
    "chat_cleanup_minutes": 0,     // hapus otomatis dashboard: 0 | 60 | 1440 (🧹 Chat)

    "servers": [                   // "Server Saya", maks. get_server_limit(user_id)
      {
        "name": "Router-A",
        "ip": "10.0.0.1",          // IP / hostname / DDNS, boleh "host:port" bila port API ≠ 8728
        "www_port": 8080,          // opsional (2.3.0): port service www untuk grafik traffic; tidak ada = 80
        "username": "read-user",
        "password": "plain-text",  // ⚠️ belum dienkripsi
        "created_at": "...",
        "updated_at": "..."
      }
    ],

    "monitoring": {                // override per user; field yang tidak ada → default global
      "normal_interval_minutes": 20,   // cek router setiap N menit
      "alert_interval_minutes": 120,   // jeda alert: notif diulang (dan dipotong) setelah N menit bila masih down
      "warning_threshold": 6,          // ⚠️ Tahap 1: pemicu notifikasi otomatis
      "critical_threshold": 12,        // 🚨 Tahap 2: eskalasi (harus > warning_threshold)
      "excluded_profiles": ["vip"],    // HANYA tambahan user; profile global admin selalu ikut
      "quiet_hours": { "start": "22:00", "end": "06:00" }  // 🌙 jam senyap (opsional; tidak ada = nonaktif)
    },

    "monitoring_state": {          // ditulis scheduler; jangan diedit manual
      "paused": false,             // true = dijeda user atau saldo habis
      "alert_active": false,       // ada server yang sedang alert
      "last_check_at": "2026-11-22 20:00:00",
      "servers": {
        "Router-A": {
          "alert_stage": 0,              // 0 normal, 1 ⚠️, 2 🚨
          "alert_window_start": "...",   // awal jeda alert (notifikasi berbayar terakhir)
          "last_alert_at": "...",
          "error_notified": false        // peringatan "tidak dapat terhubung" sudah dikirim
        }
      }
    },

    "transactions": [
      { "date": "2026-11-22 13:49:06", "amount": -125, "type": "testppp", "metadata": { "price": 125 } }
    ]
  }
}
```

Jenis `type` transaksi: [`ALUR-FITUR.md` §6](ALUR-FITUR.md#6-jenis-transaksi).
Field lama `monitoring.notify_down_threshold` (≤ 2.2.1) diabaikan sejak 2.3.0.
`settings.topup_amounts` (≤ 2.2.1) otomatis dibaca sebagai `topup_packages` tanpa QRIS (memakai QRIS umum) sampai admin menyimpan paket.

## `app_info.json`

```jsonc
{
  "app_version": "2.3.0 (...)",    // disalin dari .env saat start (send_startup_message)
  "app_name": "bot skytama",

  "settings": {                    // configs/app_settings.load_settings(); key yang tidak ada → DEFAULT_SETTINGS
    "prices": { "testppp": 125, "traffic": 50, "notify": 250 },
    "monitoring": {                // default global untuk semua user
      "normal_interval_minutes": 20,
      "alert_interval_minutes": 120,
      "warning_threshold": 6,
      "critical_threshold": 12,
      "excluded_profiles": ["expired", "pribadi-home"]   // profile global (semua user)
    },
    "trial_balance": 5000,
    "trial_mode": "manual",        // manual | auto | off
    "registration": { "hourly_limit": 10, "reject_cooldown_hours": 24 },   // 0 = tanpa batas/jeda
    "max_servers": 5,
    "topup_packages": [            // paket nominal + QRIS statik masing-masing (null → pakai qris_file_id)
      { "amount": 5000, "qris_file_id": "<file_id Telegram>" }
    ],
    "topup_custom": { "min": 10000, "max": 1000000 },   // ✍️ Nominal Lain
    "qris_file_id": "<file_id Telegram>",               // QRIS umum: nominal bebas + cadangan paket
    "refund_percent": 0,           // % saldo berbayar yang direfund saat akun dihapus
    "roles": { "<user_id>": "admin" }   // superadmin TIDAK di sini, tapi di .env
  },

  "reply_ui_cleared": [111, 222],  // chat yang sudah dibersihkan dari bar "Reply to" form lama (sekali)

  "registration_requests": {
    "<request_id>": {
      "user_id": 0, "username_telegram": "", "nohp": "628...",
      "phone_verified": true,       // sejak 2.3.0 (kontak Telegram milik akun itu)
      "trial_block_reason": null,   // alasan tidak layak trial saat diajukan (dicek ulang saat approval)
      "requested_at": "", "status": "pending | approved | rejected | duplicate",
      "trial_granted": true, "processed_by": 0, "processed_at": ""
    }
  },

  "trial_registry": {               // penerima trial; TIDAK dihapus saat akun dihapus (anti trial berulang)
    "phones": { "628...": { "user_id": 0, "at": "", "amount": 5000 } },
    "user_ids": { "<user_id>": "<waktu>" }
  },

  "refund_requests": {              // dibuat handler_refund.delete_account bila refund > 0
    "<refund_id>": {
      "user_id": 0, "name": "", "nohp": "", "balance": 0, "trial_part": 0, "paid_balance": 0,
      "percent": 50, "amount": 0, "requested_at": "", "deleted_by": 0,
      "status": "pending | paid | cancelled", "processed_by": 0, "processed_at": ""
    }
  },

  "topup_requests": {
    "<request_id>": {
      "user_id": 0, "amount": 5000, "source": "package | custom", "proof_file_id": "",
      "requested_at": "", "status": "pending | approved | rejected | cancelled (akun dihapus)",
      "processed_by": 0, "processed_at": ""
    }
  }
}
```

Saat bot start hanya `app_version` dan `app_name` yang diperbarui; isi lain dipertahankan.

## `chat_messages.json`

```jsonc
{
  "123456": {
    "all": [[1001, 1795360000.5], [1002, 1795360010.1]],  // [message_id, unix_time] ≤ 47 jam
    "ephemeral": [1002]                                  // dihapus saat aksi berikutnya
  }
}
```
Dikelola sepenuhnya oleh `configs/chat_tracker.py`. Aman dihapus kapan saja (hanya pesan lama yang tidak bisa dibersihkan otomatis lagi).

## Urutan prioritas pengaturan monitoring

```text
angka:             DEFAULT_SETTINGS (kode) ← app_info.settings.monitoring ← datauser[user].monitoring
excluded_profiles: app_info.settings.monitoring (global admin)  +  datauser[user].monitoring (tambahan user)
```
Digabung oleh `get_monitoring_config(user_record)`, yang juga menjamin ambang ≥ 1 dan 🚨 > ⚠️.

## Menambah field baru

1. Baca dengan default: `record.get("field", default)` — data lama tidak memilikinya.
2. Pengaturan admin: tambahkan ke `DEFAULT_SETTINGS` dan ke `load_settings()` bila bukan dict (lihat `PANDUAN-PENGEMBANGAN.md` §3.4).
3. Bila data lama perlu diisi, buat fungsi migrasi seperti `migrate_account_types()` dan panggil dari `main()`.
4. Perbarui contoh di dokumen ini.
