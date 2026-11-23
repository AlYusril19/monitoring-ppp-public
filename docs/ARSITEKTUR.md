# Arsitektur

Tujuan: tahu **file mana yang harus dibuka** dan **aturan apa yang berlaku** sebelum mengubah sesuatu.
Daftar fungsi lengkap per file ada di [`REFERENSI-MODUL.md`](REFERENSI-MODUL.md).

## 1. Lapisan

```text
Telegram ──► main.py ──► handlers/*  ──► configs/*  ──► datauser.json / app_info.json / chat_messages.json
 (update)    (routing)   (UI & alur)     (layanan)
                              │
                              └──► configs/mikrotik_function.py ──► RouterOS API (librouteros)
                                   configs/send_message.fetch_image ──► HTTP /graphs/iface/... (grafik)
```

| Lapisan | Isi | Aturan |
|---|---|---|
| **Entry** | `main.py` | Hanya mendaftarkan handler & scheduler (dict `COMMANDS`). Tidak ada logika bisnis. |
| **Handler** | `handlers/` | Membaca input Telegram, membalas pesan/tombol, memanggil `configs/`. |
| **Layanan** | `configs/` | Data JSON, pengaturan admin, billing, akses MikroTik, pengiriman pesan, pelacakan chat. Tidak tahu soal tombol (kecuali `navigation.py`). |
| **Sesi** | `models/userdata.py` | Router yang sedang dipakai tiap user, hanya di memori. |
| **Data** | `*.json` di root | Lihat [`DATA.md`](DATA.md). |

## 2. Perjalanan satu update Telegram

`main.py` mendaftarkan handler dalam **3 group** (PTB memproses group berurutan, satu handler per group):

```text
group -1  TypeHandler(Update, chat_tracker.before_update)   hapus balasan sementara sebelumnya
group  0  CommandHandler(...)         /command  → fungsi di COMMANDS
          CallbackQueryHandler        tombol    → handler_menu.menu_callback
          MessageHandler(photo)       foto      → handler_wallet.capture_payment_proof
          MessageHandler(text)        teks      → handler_input.handle_input
group  1  TypeHandler(Update, chat_tracker.after_update)    hapus menu yang diganti & ketikan user
```

### 2.0 Kecepatan & thread
| Thread | Isi | Aturan |
|---|---|---|
| Dispatcher (`LockedDispatcher` di `main.py`) | Memproses update satu per satu sambil memegang `DATA_LOCK` | Hanya pekerjaan cepat. |
| `router-task` (8) | `chat_tracker.in_background(...)`: cek PPPoE, traffic, daftar interface, uji koneksi form server | Tracking chat ikut terbawa; load → save sendiri wajib di dalam `with DATA_LOCK:`. |
| `chat-cleanup` (4) | Hapus pesan lama (`_delete`) & log admin (`bot_log`) | Registry diperbarui langsung; panggilan Telegram tidak menunda balasan. |
| `monitor` (8) | Job monitoring: satu user per thread (`_check_user`) | Tulis hanya lewat `_save_monitoring_state()` / `charge_user()` (keduanya memakai lock). |

- `bot` punya **connection pool 16** (`BOT_CONNECTION_POOL`). Bawaan PTB 13 untuk bot buatan sendiri hanya 1 koneksi
  yang hampir selalu dipakai long-polling, sehingga tiap balasan membuka koneksi TLS baru (penyebab bot terasa lambat).
- `datauser.json` / `app_info.json` / `chat_messages.json` ditulis **atomik** (file `.tmp` + `os.replace`).
- Uji regresi memakai `chat_tracker.SYNCHRONOUS = True` agar semua pekerjaan latar belakang berjalan berurutan.

### 2.1 Tombol → `menu_callback`
Semua tombol inline lewat satu router di `handlers/handler_menu.py`, dibagi berdasarkan prefix `callback_data`:
`nav:` `menu:` `srv:` `tr:` `clean:` `admin:` `users:` `hist:` `reg:` `topup:` `wallet:` `mon:` `onboard:` `input:`.
Tabel lengkap: [`ALUR-FITUR.md` §2](ALUR-FITUR.md#2-tombol-callback_data).

### 2.2 Teks bebas → `handle_input`
Teks dicoba ke setiap form di tuple `WIZARDS` (urutan penting):

```text
handle_onboarding_input      registrasi: no HP
handle_admin_input           pengaturan admin: harga, batas server, role, arsip, saldo trial, ...
handle_monitoring_input      ambang ⚠️/🚨 & profile tambahan user
handle_server_wizard         tambah/edit Server Saya (password dihapus dari chat)
handle_custom_server_input   Server Custom
handle_manual_topup_input    staf: tambah saldo manual
(tidak ada form terbuka)     DIAM — chat biasa tidak pernah dibalas
```

Setiap form mengembalikan `True` bila input dipakai; `handle_input` lalu memanggil `mark_input_consumed()` sehingga pesan user dihapus. Status form ada di `context.user_data` dengan key di `configs/navigation.PENDING_INPUT_KEYS`; `/cancel` dan ✖️ Batal memanggil `clear_pending_inputs()`.

### 2.3 Command → menu yang sama
Command yang punya versi tombol tidak punya logika sendiri. `handlers/handler_command_redirect.py` membuka menu tombol yang sama dengan `configs.navigation.QueryFromMessage(update)` — pembungkus yang membuat `query.edit_message_text()` mengirim pesan baru. Contoh: `/connect` → `_show_servers`, `/addserver` → `start_server_wizard`, `/daftar` (staf) → antrian registrasi, `/topup` → menu Saldo / tambah saldo manual.

## 3. Peta file

### `configs/`

| File | Isi utama | Catatan |
|---|---|---|
| `app_settings.py` | Role (`get_role`, `is_staff`, `is_superadmin`, `staff_ids`, `set_role`) · harga (`get_price`, `set_price`, `price_summary`, `PRICE_LABELS`) · saldo (`get/set_trial_balance`, `get/set_topup_amounts`, QRIS) · server (`get/set_max_servers`, **`get_server_limit`**) · monitoring (`get_monitoring_config`, `alert_level`, `ALERT_LABELS`, profile global) | **Satu sumber semua pengaturan admin.** Default di `DEFAULT_SETTINGS`, tersimpan di `app_info.json → settings`. |
| `billing.py` | `charge_user(user_id, feature) → (ok, amount, sisa)` | Satu-satunya jalur potong saldo + catat transaksi. Staf tidak dipotong. |
| `add_transaction.py` | `add_transaction(user_id, amount, type, metadata)` | Menambah riwayat transaksi user. |
| `calculate_transaction.py` | `calculate_monthly/yearly_transactions` | Ringkasan riwayat satu user (bulan 1–12). |
| `data_json_user.py` | `load/save_user_data`, `load/save_app_info`, `get_registered_username`, `migrate_account_types` | **Satu-satunya** tempat baca/tulis `datauser.json` & `app_info.json`. |
| `send_message.py` | `bot` (**`TrackingBot`**), `bot_log`, `chat_log`, `allowed_admin_ids`, `send_message`, `send_down_report`, `fetch_image`, `escape_md` | Membaca `.env` saat di-import. `TrackingBot`: tanpa quote, pesan > 4096 dipecah, semua pesan dicatat `chat_tracker`, log tidak pernah tertimpa. |
| `chat_tracker.py` | `before_update`, `after_update`, `keep_messages`, `mark_input_consumed`, `track_message`, `clear_chat` | Chat ringkas (§6). |
| `navigation.py` | `home_keyboard`, `back_keyboard`, `cancel_keyboard`, `topup_keyboard`, `session_action_keyboard`, `wizard_keyboard`, `dashboard_row`, `clear_pending_inputs`, `QueryFromMessage` | Semua keyboard & status form yang dipakai ulang. |
| `mikrotik_function.py` | `get_down_users`, `get_name_server`, `get_graphing_interfaces`, `get_interface_details` | Semua query RouterOS. Tanpa profile hard-code. |
| `chat_cleanup.py` | `schedule_cleanup` | Hapus dashboard otomatis setelah N menit (pilihan 🧹 Chat). |
| `get_current_time.py` · `format_rupiah.py` | waktu WIB · `Rp1.234` | |

### `handlers/`

| Area | File | Isi |
|---|---|---|
| Routing | `handler_menu.py` | `show_menu`, `_user_dashboard_keyboard` (juga User Testing), dashboard admin, `menu_callback`, Server Saya, pilih interface traffic, `_admin_callback`. |
| | `handler_command_redirect.py` | Command lama → menu tombol; `/cancel`. |
| | `handler_input.py` | Rantai form teks (`WIZARDS`). |
| Registrasi & akun | `handler_onboarding.py` | Ajukan registrasi, antrian & approval (trial/tanpa/tolak), hapus akun. |
| | `handler_user.py` | 👥 Data User: aktif/arsip/saldo, `set_user_active`. |
| Server | `handler_server.py` | Form tambah/edit Server Saya, `server_limit_reached`. |
| PPPoE | `handler_start.py` | `run_pppoe_test` (log 1 pesan), Server Custom, `/testppp`, `/custom`. |
| Traffic | `handler_traffic.py` | `run_traffic_monitoring` (ambil grafik dulu, baru potong saldo). |
| Monitoring | `check_client_status_and_notify.py` | Job scheduler 2 tahap (§4). |
| | `handler_monitor_settings.py` | Menu ⚙️ Monitoring per user (`mon:`). |
| Saldo | `handler_wallet.py` | Nominal → QRIS → bukti transfer → antrian & approval; tambah saldo manual; `/setqris`; `user_label`. |
| | `handler_saldo_cek.py` · `handler_transaction.py` · `handler_all_transaction.py` | `/saldo` · riwayat user · laporan pendapatan admin. |
| Admin | `handler_admin_settings.py` | Menu ⚙️ Harga & Role, `ADMIN_INPUTS`, `apply_admin_input` (dipakai tombol **dan** `/set...`). |
| Info | `handler_info.py` · `handler_biaya.py` · `handler_version.py` · `handler_warning.py` | `/info` & `/version` beda isi untuk user/admin (`is_admin_view`), 💸 Biaya, `/why`, `/infonotify`. |
| Lain | `handler_exit.py` · `send_startup_message.py` | `/exit` · pesan startup + penutup bar "Reply to" lama. |

## 4. Monitoring otomatis (2 tahap)

`main.py` menjalankan `check_client_status_and_notify` **setiap 60 detik**. Router tiap user dicek setiap `normal_interval_minutes` (juga saat alert, agar kenaikan ke 🚨 terdeteksi).

Level dari `app_settings.alert_level()`: **0** normal · **1** down ≥ `warning_threshold` (⚠️) · **2** down ≥ `critical_threshold` (🚨).

```text
user arsip / paused / belum waktunya → lewati
untuk setiap server tersimpan:
  gagal terhubung  → peringatan SEKALI (error_notified); terhubung lagi → "kembali terhubung"
  level 0          → bila sebelumnya alert: "sudah pulih", reset
  level ≥1, tidak ada jeda aktif        → charge_user("notify"); buka jeda; kirim notifikasi
  level naik di dalam jeda (⚠️→🚨)      → kirim eskalasi, GRATIS
  level sama/turun di dalam jeda        → diam
  jeda (alert_interval_minutes) habis, masih ≥1 → pengingat, dipotong lagi, jeda baru
  saldo kurang     → monitoring user di-pause (lanjutkan dari ⚙️ Monitoring)
```

- Notifikasi = **1 pesan** (`send_down_report`): header, daftar nama, label, biaya; daftar panjang → lampiran `.txt`.
- Status per server di `monitoring_state.servers[nama]`: `alert_stage`, `alert_window_start`, `last_alert_at`, `error_notified`.
- Status disimpan **sebelum** pesan dikirim (pesan gagal tidak menyebabkan potongan ganda).
- User dicek **paralel** (`USER_WORKERS`); router yang timeout tidak menunda user lain. ⏸ Jeda yang ditekan saat pengecekan berjalan tetap dipertahankan.
- **Penting:** job membaca `datauser.json` sekali di awal. Jangan `save_user_data()` snapshot itu; pakai `_save_monitoring_state()` / `_save_state_flags()` yang hanya menulis `monitoring_state` ke data terbaru.

Konfigurasi efektif (`get_monitoring_config`):
- angka: `DEFAULT_SETTINGS` ← `app_info.settings.monitoring` ← `datauser[user].monitoring`; dijamin ≥ 1 dan 🚨 > ⚠️;
- `excluded_profiles` = **profile global admin** (default `expired`, `pribadi-home`) **+ profile tambahan user**.

Cek PPPoE manual (`run_pppoe_test`) selalu dipotong `testppp` setelah login berhasil dan selalu menampilkan **semua** nama yang down; ambang hanya menentukan label.

## 5. Sesi & state di memori

Hilang saat bot restart:

| Lokasi | Isi |
|---|---|
| `models.userdata.user_data_dict[user_id]` | `UserData`: `ip_address`, `router_username`, `router_password`, `interface`, `server_name` (`None` = Server Custom). |
| `context.user_data` | Status form (`PENDING_INPUT_KEYS`) dan `user_testing_mode`. |

## 6. Chat ringkas (`configs/chat_tracker.py`)

- Semua pesan bot di chat pribadi dicatat di `chat_messages.json` (≤ 47 jam; batas hapus Telegram 48 jam).
- Pesan yang dikirim **saat menangani update** chat itu = **sementara** → dihapus di `before_update` berikutnya.
- Menu yang ditekan dihapus di `after_update` bila diganti pesan baru (bukan diedit). Command & isian form user dihapus setelah diproses.
- **Log** (tetap): dibungkus `with keep_messages():` (hasil Cek PPPoE, grafik traffic), atau dikirim di luar update (notifikasi otomatis, pesan ke admin, pesan ke user dari aksi admin).
- Log tidak pernah tertimpa: `TrackingBot.edit_message_text` mengirim pesan baru bila targetnya log (`is_protected`).
- 🗑 Bersihkan (`clean:all`) → `clear_chat()` menghapus semua pesan tercatat.
- Pesan startup ditandai sementara lewat `track_message()`.

## 7. Peran

| Role | Sumber | Hak |
|---|---|---|
| `superadmin` | ID di `ALLOWED_ADMIN_IDS` (`.env`) | Semua hak admin + ⚙️ Harga & Role, QRIS, role. |
| `admin` / `operator` | `app_info.settings.roles` (via `/setrole` atau 🛡 Atur Role) | Approval registrasi/topup, saldo manual, Data User, laporan. |
| `user` | default | Fitur monitoring & saldo sendiri. |

Staf tidak dipotong biaya. Staf melihat dashboard admin; 🧪 User Testing membuka dashboard user asli (record uji saldo 0) dan `/info`/`/version` versi user.

## 8. Integrasi MikroTik

| Kebutuhan | Perintah RouterOS |
|---|---|
| Pelanggan down | `/ppp/secret/print` dikurangi `/ppp/active/print`, tanpa profile yang dikecualikan |
| Nama router | `/system/identity/print` |
| Interface traffic | `/tool/graphing/interface/print` — entry spesifik aktif → itu saja; entry `all` aktif → semua `/interface/print`; tidak ada → tidak ditawarkan. Komentar interface ditampilkan. |
| Grafik | HTTP `http://HOST/graphs/iface/INTERFACE/daily.gif` (`fetch_image`) |

Gunakan akun RouterOS **read-only**. Password dihapus dari chat setelah dibaca, tetapi tersimpan **plain text** di `datauser.json` (lihat [`CATATAN-TEKNIS.md`](CATATAN-TEKNIS.md)).

## 9. Telegram: perilaku umum

- Bot = `TrackingBot(ExtBot)` dengan `Defaults(quote=False)`: pesan bot tidak pernah mengutip pesan user.
- `start_polling(drop_pending_updates=True)`: pesan yang masuk saat bot mati diabaikan (tidak dibalas beruntun).
- Pesan > 4096 karakter otomatis dipecah; daftar down panjang → 1 pesan + lampiran `.txt`.
- Teks dinamis di Markdown wajib `escape_md()`.
- `send_startup_message` (saat start): perbarui `app_version` di `app_info.json` (data lain dipertahankan), tutup bar "Reply to" form lama sekali per chat (`clear_reply_interface`), kabari user aktif.
