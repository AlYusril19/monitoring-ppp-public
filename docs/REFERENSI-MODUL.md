# Referensi Modul

> Dibuat otomatis oleh `tools/buat_referensi.py` pada 23/11/2026. Jangan diedit manual: ubah docstring di kode lalu jalankan ulang.
> Fungsi berawalan `_` adalah internal modul. Alur & aturan: [`ARSITEKTUR.md`](ARSITEKTUR.md).

## Entry point

### `main.py`

Konstanta: `COMMANDS`, `STAFF_COMMANDS`

| Fungsi | Keterangan |
|---|---|
| class `LockedDispatcher` | Handles one update at a time while holding DATA_LOCK. |
| &nbsp;&nbsp;`.process_update(self, update)` | Proses satu update sambil memegang DATA_LOCK. |
| `main()` | Daftarkan semua handler, scheduler monitoring, lalu jalankan bot (polling). |

## configs/ — layanan (data, pengaturan, billing, Telegram, MikroTik)

### `configs/access.py`
Access control in one place: which buttons/commands are staff-only.

Konstanta: `STAFF_CALLBACK_PREFIXES`, `GUEST_CALLBACKS`, `_REPORT_INTERVAL`

| Fungsi | Keterangan |
|---|---|
| `is_registered(user_id)` | True bila user punya record di datauser.json. |
| `report_denied(user, what)` | Catat percobaan akses fitur admin oleh non-staf ke chat log (dibatasi per user). |
| `callback_allowed(query)` | Cek tombol sebelum diproses. Mengembalikan False (dan menjawab query) bila ditolak. |
| `staff_only(handler)` | Bungkus command khusus staf: non-staf mendapat penolakan singkat dan dicatat. |

### `configs/add_transaction.py`

| Fungsi | Keterangan |
|---|---|
| `add_transaction(user_id, amount, transaction_type, metadata)` | Tambah satu baris riwayat ke datauser[user].transactions (amount +masuk / -pemakaian). |
| `_append(user_id, amount, transaction_type, metadata)` | Isi add_transaction (dipanggil saat DATA_LOCK dipegang). |

### `configs/app_settings.py`
Persistent, Telegram-managed application settings.

Konstanta: `PRICE_LABELS`, `DEFAULT_SETTINGS`, `TRIAL_MODES`, `MAX_TOPUP_PACKAGES`, `ALERT_LABELS`

| Fungsi | Keterangan |
|---|---|
| `load_settings()` | Gabungkan DEFAULT_SETTINGS dengan app_info.json → settings; selalu mengembalikan nilai lengkap. |
| `_clean_packages(packages)` | Validasi daftar paket topup tersimpan; None bila tidak ada/rusak ([] tetap sah). |
| `save_settings(settings)` | Simpan dict settings ke app_info.json (data lain di file itu dipertahankan). |
| `_update_setting(key, value)` | Ubah satu key settings lalu simpan. |
| `get_role(user_id)` | Role user: superadmin (.env), admin/operator (settings.roles), atau user. |
| `is_staff(user_id)` | True untuk superadmin, admin, dan operator (tidak dipotong biaya, boleh approval). |
| `is_superadmin(user_id)` | True hanya untuk ID di ALLOWED_ADMIN_IDS (.env). |
| `staff_ids()` | Superadmins from .env plus admin/operator roles set via Telegram. |
| `set_role(user_id, role)` | Atur role admin/operator/user; juga menandai account_type di datauser.json. |
| `get_price(feature)` | Harga fitur (testppp/traffic/notify) dalam rupiah. |
| `set_price(feature, amount)` | Ubah harga satu fitur yang ada di PRICE_LABELS. |
| `price_summary()` | One price list text, reused by /biaya, /settings and the admin menu. |
| `get_trial_balance()` | Saldo trial untuk registrasi yang disetujui dengan trial. |
| `set_trial_balance(amount)` | Ubah saldo trial registrasi. |
| `get_trial_mode()` | Mode pemberian trial: manual / auto / off (lihat TRIAL_MODES). |
| `set_trial_mode(mode)` | Ubah mode pemberian trial. |
| `get_registration_limits()` | {'hourly_limit', 'reject_cooldown_hours'} untuk keamanan registrasi (nilai >= 0). |
| `set_registration_limit(key, value)` | Ubah satu batas registrasi (hourly_limit / reject_cooldown_hours), nilai >= 0. |
| `get_refund_percent()` | Persentase saldo berbayar yang direfund sebagai uang saat akun dihapus (0-100). |
| `set_refund_percent(percent)` | Ubah persentase refund (0-100). |
| `get_topup_packages()` | Paket topup [{'amount', 'qris_file_id'}], urut nominal. |
| `get_topup_package(amount)` | Satu paket topup berdasarkan nominal, atau None. |
| `get_topup_amounts()` | Nominal semua paket topup. |
| `_save_packages(packages)` | Simpan daftar paket (urut nominal). |
| `add_topup_package(amount, qris_file_id)` | Tambah paket nominal baru beserta QRIS statiknya. |
| `update_topup_package(amount, new_amount, qris_file_id)` | Ubah nominal dan/atau QRIS satu paket. |
| `delete_topup_package(amount)` | Hapus satu paket topup. |
| `get_custom_topup_range()` | (min, max) nominal bebas yang boleh diketik user. |
| `set_custom_topup_range(minimum, maximum)` | Ubah batas nominal bebas (min >= 1, max > min). |
| `get_qris_file_id()` | file_id QRIS umum (nominal bebas & cadangan paket tanpa QRIS), atau None. |
| `set_qris_file_id(file_id)` | Simpan file_id QRIS umum. |
| `package_qris(amount)` | QRIS satu paket: QRIS paket itu, atau QRIS umum sebagai cadangan. |
| `get_max_servers()` | Batas global jumlah Server Saya per user (default 5). |
| `set_max_servers(amount)` | Ubah batas global jumlah server (minimal 1). |
| `get_server_limit(user_id)` | Maximum saved servers for this user. |
| `get_global_excluded_profiles()` | Profile PPPoE yang dikecualikan untuk semua user (diatur admin). |
| `set_global_excluded_profiles(profiles)` | Ubah daftar profile global yang dikecualikan. |
| `_clean_profiles(profiles)` | Normalisasi daftar profile: trim, buang kosong & duplikat (tanpa beda huruf besar/kecil). |
| `alert_level(down_count, config)` | 0 = normal, 1 = Warning ⚠️, 2 = Warning 🚨. |
| `get_monitoring_config(user_record)` | Effective monitoring config for one user. |
| `_minutes(text)` | 'HH:MM' (24 jam) -> menit sejak 00:00; ValueError bila tidak valid. |
| `parse_quiet_hours(text)` | Teks '22:00-06:00' -> {'start': '22:00', 'end': '06:00'}; '-' -> None; ValueError bila salah. |
| `_clean_quiet_hours(value)` | Jam senyap tersimpan yang valid, atau None (data lama/rusak = nonaktif). |
| `in_quiet_hours(quiet, now)` | True bila waktu `now` (datetime) berada di jam senyap [start, end); mendukung lewat tengah malam. |
| `quiet_hours_label(quiet)` | Teks jam senyap untuk tampilan. |

### `configs/billing.py`
Single charging path so every transaction retains its price snapshot.

| Fungsi | Keterangan |
|---|---|
| `charge_user(user_id, feature)` | Return ``(success, amount, remaining_balance)``. |

### `configs/calculate_transaction.py`

| Fungsi | Keterangan |
|---|---|
| `calculate_monthly_transactions(user_id, year)` | Return {month_number: {"income": x, "expenses": y}} for one user and year. |
| `calculate_yearly_transactions(user_id, year)` | Total (saldo masuk, pemakaian) satu user dalam setahun. |

### `configs/chat_cleanup.py`
Best-effort cleanup for messages created by this bot.

| Fungsi | Keterangan |
|---|---|
| `schedule_cleanup(context, message, minutes)` | Jadwalkan penghapusan satu pesan setelah N menit (0 = tidak). |
| `_delete_message(context)` | Job: hapus pesan terjadwal; error diabaikan. |

### `configs/chat_tracker.py`
Keep private chats short: bot replies are temporary, monitoring results are logs.

Konstanta: `STORE_FILE`, `MAX_AGE_SECONDS`, `SYNCHRONOUS`

| Fungsi | Keterangan |
|---|---|
| `_load()` | Baca chat_messages.json saat modul dimuat. |
| `_save()` | Tulis registry pesan ke chat_messages.json. |
| `_chat(chat_id)` | Ambil entri satu chat dan buang ID yang lebih tua dari MAX_AGE_SECONDS. |
| `_remember(chat_id, message_id, ephemeral)` | Catat satu pesan; ephemeral=True berarti dihapus saat aksi berikutnya. |
| `_forget(chat_id, message_ids)` | Hapus ID pesan dari registry. |
| `_delete_now(bot, chat_id, message_ids)` | Panggil deleteMessage untuk tiap ID (abaikan error). |
| `_delete(bot, chat_id, message_ids)` | Lupakan pesan di registry sekarang, hapus di Telegram di latar belakang (tidak menunda balasan). |
| `submit_quick(function, *args)` | Kirim pekerjaan singkat (hapus pesan, log admin) ke pool latar belakang. |
| `in_background(function, *args, **kwargs)` | Run slow work (router check) off the dispatcher thread, keeping this chat's message tracking. |
| `_active_chat()` | Chat yang sedang diproses di thread ini, atau None. |
| `on_sent(message)` | Called by TrackingBot for every message it sends. |
| `on_edited(message_id)` | Catat bahwa pesan ini diedit selama update berjalan (bukan diganti). |
| `is_protected(message_id)` | True for the log message whose button was pressed: never overwrite it. |
| `track_message(message)` | Mark a message sent outside an update (e.g. startup notice) as temporary. |
| `keep_messages()` | Messages sent inside this block stay in the chat as a log. |
| `mark_input_consumed()` | A form used the user's message; it is deleted after handling. |
| `before_update(update, context)` | Group -1: delete the previous temporary replies of this chat. |
| `after_update(update, context)` | Group 1: tidy up the pressed button message and the user's own input. |
| `clear_chat(bot, chat_id, keep_ids)` | Delete every recorded message of the chat (bot replies, logs, user input). |

### `configs/data_json_user.py`
JSON storage (datauser.json, app_info.json).

Konstanta: `BASE_DIR`, `USER_DATA_FILE`, `APP_INFO_FILE`, `DATA_LOCK`

| Fungsi | Keterangan |
|---|---|
| `write_json_atomic(path, data, indent)` | Tulis JSON ke file sementara lalu ganti file asli sekaligus (tidak pernah setengah jadi). |
| `_read_json(path)` | Baca file JSON; {} bila belum ada atau rusak. |
| `migrate_account_types()` | Mark existing records as admin/client without changing balances or servers. |
| `load_user_data()` | Baca datauser.json; {} bila belum ada/rusak. |
| `save_user_data(data)` | Tulis seluruh datauser.json (atomik). |
| `get_registered_username(user_id)` | Return the display name recorded at registration, never live Telegram data. |
| `save_app_info(info)` | Tulis seluruh app_info.json (pengaturan & antrian, atomik). |
| `load_app_info()` | Baca app_info.json; {} bila belum ada/rusak. |

### `configs/format_rupiah.py`

| Fungsi | Keterangan |
|---|---|
| `format_rupiah(amount)` | Format angka menjadi 'Rp1.234'. |

### `configs/get_current_time.py`

| Fungsi | Keterangan |
|---|---|
| `get_current_time(timezone_name, format_string)` | Get the current time formatted as per the specified timezone and format string. |

### `configs/mikrotik_function.py`
RouterOS helpers: connect, PPPoE status, interfaces, and friendly connection errors.

Konstanta: `DEFAULT_API_PORT`, `DEFAULT_WWW_PORT`, `_HOST_RE`, `_ERROR_TEXTS`, `_PORT_HINT`

| Fungsi | Keterangan |
|---|---|
| class `RouterError` | Router could not be reached or answered with an error; `kind` says why. |
| `classify_router_error(exc)` | Map a connect/API exception to login, timeout, refused, host, offline or other. |
| `split_host_port(address, default_port)` | 'host', 'host:port' or '[ipv6]:port' -> (host, port); ValueError on a bad port. |
| `validate_address(address)` | Pesan error bila alamat router tidak valid, None bila valid. |
| `ping_host(host)` | One ping: True = replied, False = no reply, None = ping not available here. |
| `diagnose_address(kind, address)` | Ping the router to tell 'wrong IP / router down' from 'wrong port' (Markdown, or ''). |
| `router_error_text(exc, name, address)` | Pesan ramah (Markdown) untuk kegagalan koneksi router, plus diagnosa ping bila `address` diberikan. |
| `connect_router(address, username, password)` | Connect + login to RouterOS at 'host' or 'host:port'; raise RouterError on failure. |
| `graph_url(address, interface, www_port)` | URL grafik harian Tools > Graphing; port API di alamat diabaikan, port web dari pengaturan server. |
| `get_down_users(connection, excluded_profiles)` | Return [(name, last_logged_out)] for PPP secrets that are not active. |
| `get_name_server(connection)` | Nama router dari /system/identity, atau None. |
| `get_graphing_interfaces(connection)` | Return only interfaces enabled in RouterOS Tools > Graphing. |
| `get_interface_details(connection)` | Return interface name and RouterOS comment for friendly button labels. |

### `configs/navigation.py`

Konstanta: `PENDING_INPUT_KEYS`

| Fungsi | Keterangan |
|---|---|
| `clear_pending_inputs(context)` | Cancel any open form. Returns True when something was cancelled. |
| class `QueryFromMessage` | Lets a menu written for inline buttons open from a /command. |
| &nbsp;&nbsp;`.answer(self, *args, **kwargs)` | Tidak melakukan apa pun (command tidak punya callback untuk dijawab). |
| &nbsp;&nbsp;`.edit_message_text(self, text, **kwargs)` | Kirim pesan baru karena command tidak punya pesan tombol untuk diedit. |
| `home_keyboard(label)` | Satu tombol 🏠 Dashboard (label bisa diganti). |
| `session_action_keyboard()` | Single action panel displayed after a completed router operation. |
| `wizard_keyboard(kind)` | Tombol ↩️ Reset Input + ✖️ Batal untuk form server. |
| `cancel_keyboard()` | For every prompt that waits for typed input. |
| `back_keyboard(back_data, back_label)` | Back to the previous menu + Dashboard, for results inside a sub-menu. |
| `topup_keyboard()` | When the balance is not enough. |
| `dashboard_row()` | Satu baris berisi tombol 🏠 Dashboard, untuk ditambahkan ke keyboard lain. |

### `configs/send_message.py`

Konstanta: `BOT_CONNECTION_POOL`, `TEXT_LIMIT`, `SAFE_TEXT_LIMIT`, `CAPTION_LIMIT`

| Fungsi | Keterangan |
|---|---|
| `_request(pool_size)` | HTTP pool for a Bot (None in tests). |
| `_split_text(text, limit)` | Split on line breaks so each part fits in one Telegram message. |
| class `TrackingBot` | Bot that records its messages so temporary replies can be cleaned up. |
| &nbsp;&nbsp;`.send_message(self, *args, **kwargs)` | Kirim teks; teks > 4096 karakter otomatis dipecah. Pesan dicatat chat_tracker. |
| &nbsp;&nbsp;`.send_document(self, *args, **kwargs)` | Kirim file dan catat di chat_tracker. |
| &nbsp;&nbsp;`.send_photo(self, *args, **kwargs)` | Kirim foto dan catat di chat_tracker. |
| &nbsp;&nbsp;`.edit_message_text(self, *args, **kwargs)` | Edit pesan; bila targetnya log monitoring, kirim pesan baru agar log tidak tertimpa. |
| class `_BackgroundLogBot` | Admin log bot: messages are sent in the background so a log never delays the user's reply. |
| &nbsp;&nbsp;`.send_message(self, *args, **kwargs)` | Kirim log tanpa menunggu (hasil tidak dipakai pemanggil). |
| &nbsp;&nbsp;`._send_quietly(self, args, kwargs)` | Kirim log; kegagalan hanya dicetak. |
| `escape_md(value)` | Escape text for Telegram legacy Markdown (parse_mode='markdown'). |
| `send_message(bot, chat_id, message, with_dashboard, reply_markup)` | Send Markdown text. Final messages should pass with_dashboard=True or a reply_markup. |
| `fetch_image(image_url, timeout)` | Download an image; return BytesIO, or None if it is not a usable image. |
| `send_down_report(bot, chat_id, header, down_users, footer, reply_markup)` | Send a PPPoE DOWN list as ONE message, whatever its length. |

## handlers/ — fitur Telegram (menu, form, monitoring)

### `handlers/check_client_status_and_notify.py`
Automatic PPPoE monitoring job (runs every 60 s, see main.py).

Konstanta: `TIMEZONE`, `USER_WORKERS`

| Fungsi | Keterangan |
|---|---|
| `_save_monitoring_state(user_id, state)` | Write only this user's monitoring_state onto fresh data. |
| `_parse(text)` | Ubah teks 'YYYY-mm-dd HH:MM:SS' menjadi datetime WIB. |
| `_save_state_flags(user_id, state)` | Hitung ulang alert_active user lalu simpan monitoring_state. |
| `_safe_send(bot, chat_id, text, reply_markup)` | Kirim pesan tanpa menghentikan job bila gagal (mis. user memblokir bot). |
| `check_client_status_and_notify(context)` | Job tiap 60 detik: cek semua server user yang jatuh tempo dan kirim notifikasi 2 tahap. |
| `_check_user(bot, user_id, data, now, now_text)` | Cek semua server satu user (dipanggil paralel oleh job). |

### `handlers/handler_admin_settings.py`
Admin settings: one implementation used by both /commands and buttons.

Konstanta: `ADMIN_INPUTS`

| Fungsi | Keterangan |
|---|---|
| `_input_spec(key)` | (prompt, superadmin_only) untuk key, termasuk key berparameter seperti 'pkg_edit:5000'. |
| `_parse_amount(text, minimum)` | Ubah teks angka ('5.000', '5000') menjadi int dan cek nilai minimal. |
| `apply_admin_input(user_id, key, value)` | Validate and save one setting. Returns text or AdminReply; raises ValueError/PermissionError. |
| `settings_text(user_id)` | Ringkasan semua pengaturan saat ini (Markdown). |
| `admin_settings_menu(query)` | Menu ⚙️ Harga & Role; tombol ubah hanya untuk superadmin. |
| `trial_menu(query)` | Menu 🎁 Trial & Registrasi (di 👥 Data User): ketentuan trial dan anti registrasi massal. |
| `set_trial_mode_callback(query, mode)` | Tombol admin:trialmode:<manual/auto/off> (superadmin). |
| `start_admin_input(query, context, key)` | Buka form untuk satu key ADMIN_INPUTS setelah cek hak akses. |
| `handle_admin_input(update, context)` | Consume the answer to an admin setting prompt. Returns True if consumed. |
| `_after_input_keyboard(key)` | After saving, go back to the menu the setting came from. |
| `_run_command(update, key, usage, args)` | Jalankan apply_admin_input dari /command dan balas hasil/kesalahannya. |
| `settings_command(update, context)` | /settings: tampilkan ringkasan pengaturan + daftar command. |
| `set_price_command(update, context)` | /setprice <fitur> <nominal>. |
| `set_role_command(update, context)` | /setrole <user_id> <role>. |
| `set_trial_command(update, context)` | /settrial <nominal>. |
| `set_max_server_command(update, context)` | /setmaxserver <jumlah>. |

### `handlers/handler_all_transaction.py`
Revenue reports for staff (/laporanbulanan, /laporantahunan, 📊/📈 buttons).

Konstanta: `MONTHS`

| Fungsi | Keterangan |
|---|---|
| `_totals(transactions, year, month)` | Jumlahkan saldo masuk & pemakaian dari daftar transaksi (trial diabaikan). |
| `_report(update, context, year, month)` | Susun dan kirim laporan semua user untuk satu tahun / bulan. |
| `check_monthly_user_transactions(update, context)` | /laporanbulanan [bulan] dan tombol 📊. |
| `check_yearly_user_transactions(update, context)` | /laporantahunan [tahun] dan tombol 📈. |

### `handlers/handler_biaya.py`
💸 Biaya (/biaya and the button under /info).

| Fungsi | Keterangan |
|---|---|
| `user_cost_text(record)` | Rincian biaya untuk user: harga, kapan dipotong, apa yang gratis (pakai ambang user). |
| `staff_cost_text()` | Daftar harga + catatan bahwa staf tidak dipotong biaya. |
| `biaya_fitur(update, context)` | /biaya dan tombol 💸 Biaya (isi sesuai peran). |

### `handlers/handler_command_redirect.py`
Text commands that open the same button menus (one implementation per feature).

| Fungsi | Keterangan |
|---|---|
| `_registered(update)` | True bila user terdaftar; bila tidak, kirim petunjuk registrasi. |
| `servers_command(update, context)` | /listserver, /connect, /editserver, /delserver → Server Saya (pilih, ⚙️ Kelola). |
| `add_server_command(update, context)` | /addserver → wizard Tambah server (password dihapus, batas server dicek). |
| `daftar_command(update, context)` | /daftar → staf: antrian registrasi; calon user: tombol registrasi. |
| `topup_command(update, context)` | /topup → staf: tambah saldo manual; user: menu Saldo (QRIS + bukti). |
| `cancel_command(update, context)` | /cancel: close any open form (registration, server, topup, admin input...). |

### `handlers/handler_exit.py`

| Fungsi | Keterangan |
|---|---|
| `exit_command_handler(update, context)` | /exit: hapus sesi router (Server Saya/Custom) dari memori. |

### `handlers/handler_info.py`
/info and /infonotify texts.

| Fungsi | Keterangan |
|---|---|
| `is_admin_view(user_id, context)` | Staff see admin texts, except while testing the customer view. |
| `info_keyboard()` | Tombol di bawah /info: Biaya, Info Notify, Versi, Dashboard. |
| `_footer()` | Nama aplikasi + versi dari .env. |
| `user_info_messages(user_id, record)` | Isi /info untuk user: akun, cara menggunakan, perintah cepat. |
| `admin_info_messages(user_id)` | Isi /info untuk staf: panduan admin, pengaturan, biaya & pendapatan, command. |
| `infolengkap_command_handler(update, context)` | /info dan tombol ℹ️ Info (isi sesuai peran). |
| `notify_command_handler(update, context)` | /infonotify: penjelasan monitoring otomatis dengan nilai milik user. |

### `handlers/handler_input.py`
Route free text to whichever form (wizard) is currently open for this chat.

Konstanta: `WIZARDS`

| Fungsi | Keterangan |
|---|---|
| `handle_input(update, context)` | Teks bebas: teruskan ke form yang sedang terbuka (WIZARDS); tanpa form → diam. |

### `handlers/handler_menu.py`
Inline-keyboard navigation for the main customer workflow.

Konstanta: `GRAPHING_GUIDE`

| Fungsi | Keterangan |
|---|---|
| `show_menu(update, context)` | /start, /menu, tombol Dashboard: dashboard sesuai peran, atau tombol registrasi. |
| `_user_dashboard_keyboard(user_id, testing)` | Single source for the user dashboard. |
| `_send_user_dashboard(update, context, testing)` | Kirim dashboard user (juga dipakai User Testing). |
| `_send_admin_dashboard(update, context)` | Kirim dashboard admin. |
| `menu_callback(update, context)` | Router SEMUA tombol inline berdasarkan prefix callback_data (lihat docs/ALUR-FITUR.md §2). |
| `_show_servers(query)` | Menu Server Saya: daftar server, Kelola, Tambah (n/batas). |
| `_show_server_manage(query, index)` | Menu Kelola satu server: edit / hapus. |
| `_delete_server(query, index)` | Hapus server dari datauser dan putuskan sesi bila sedang dipakai. |
| `_ask_delete_server(query, index)` | Konfirmasi hapus server. |
| `_connect_server(query, index)` | Pakai server tersimpan sebagai sesi router aktif. |
| `_show_traffic_servers(query)` | Pilih server untuk Monitor Traffic. |
| `_show_interfaces(query, index)` | Daftar interface yang aktif di Tools > Graphing router. |
| `_run_traffic(query, context, server_ref, interface)` | Set interface pilihan lalu jalankan run_traffic_monitoring. |
| `_servers_for(user_id)` | Daftar Server Saya milik user. |
| `_require_connection(query)` | True bila user sudah punya sesi router. |
| `_prompt_server_before_pppoe(query)` | Minta user memilih server sebelum Monitor PPPoE. |
| `_set_cleanup(query, minutes)` | Simpan pilihan hapus-otomatis dashboard (menit). |
| `_admin_callback(update, context)` | Router tombol admin:* (cek is_staff dulu). |
| `_ensure_staff_test_record(user)` | Give staff a zero-balance private record for server/UI testing only. |
| `_input_wizard_callback(query, context)` | Tombol ✖️ Batal / ↩️ Reset di form. |

### `handlers/handler_monitor_settings.py`

| Fungsi | Keterangan |
|---|---|
| `_keyboard()` | Keyboard menu ⚙️ Monitoring. |
| `_summary(record)` | Ringkasan pengaturan monitoring user (Markdown). |
| `monitoring_settings(update, context)` | /monitoring dan tombol ⚙️ Monitoring. |
| `monitoring_callback(query, context)` | Tombol mon:* (interval, jeda, ambang, profile, pause/resume). |
| `handle_monitoring_input(update, context)` | Form angka ambang ⚠️/🚨 atau daftar profile tambahan user. |

### `handlers/handler_onboarding.py`
Button-led registration and account deletion for private Telegram chats.

Konstanta: `TIME_FORMAT`

| Fungsi | Keterangan |
|---|---|
| `normalize_phone(text)` | Nomor telepon -> hanya digit berawalan 62 (08xx / 8xx / +62xx dianggap sama). |
| `_hours_since(text)` | Jam sejak waktu 'YYYY-mm-dd HH:MM:SS' (WIB); angka besar bila tidak valid. |
| `remove_reply_keyboard(bot, chat_id)` | Tutup tombol 📱 Kirim Nomor (reply keyboard) tanpa meninggalkan pesan. |
| `registration_block_reason(user_id, app_info)` | Alasan user belum boleh mengajukan registrasi, atau None bila boleh. |
| `trial_block_reason(user_id, phone, app_info, users)` | Alasan trial tidak boleh diberikan, atau None bila memenuhi syarat. |
| `_remember_trial(app_info, user_id, phone, amount)` | Catat penerima trial agar nomor/akun yang sama tidak mendapat trial lagi. |
| `new_user_menu(update, context)` | Pesan sambutan + tombol ✨ Ajukan Registrasi untuk user baru. |
| `onboarding_callback(query, context)` | Tombol onboard:* (mulai registrasi, hapus akun). |
| `_start_registration(query, context)` | onboard:register: cek batas, lalu minta nomor lewat tombol kontak Telegram. |
| `handle_onboarding_input(update, context)` | Teks saat registrasi menunggu kontak: arahkan ke tombol (nomor ketikan tidak diterima). |
| `handle_contact(update, context)` | Kontak dibagikan (tombol 📱 Kirim Nomor Saya): buat pengajuan registrasi terverifikasi. |
| `_approval_keyboard(request_id, request, with_back)` | Tombol keputusan sesuai mode trial dan kelayakan trial pengajuan ini. |
| `_request_text(request_id, request)` | Ringkasan pengajuan untuk staf, termasuk tanda risiko. |
| `registration_approval_callback(query, context)` | Approve registration (with trial when allowed), or reject it. |
| `pending_registrations_menu(query)` | Daftar antrian registrasi untuk staf. |
| `registration_queue_callback(query, context)` | Detail satu pengajuan registrasi + tombol keputusan. |
| `_notify_staff_registration(context, request_id, request)` | Kirim pengajuan registrasi baru ke semua staf. |

### `handlers/handler_refund.py`
Account deletion with a balance refund notice, and the staff refund queue.

| Fungsi | Keterangan |
|---|---|
| `refund_quote(user_id)` | Hitung refund untuk satu user; None bila user tidak terdaftar. |
| `deletion_notice(quote)` | Pemberitahuan refund (Markdown) sebelum akun dihapus. |
| `deletion_result_text(result, by_admin)` | Pesan hasil penghapusan untuk user (by_admin=False) atau untuk admin (True). |
| `delete_account(bot, user_id, deleted_by)` | Hapus akun, batalkan topup yang menunggu, buat permintaan refund. None bila tidak ada. |
| `_refund_keyboard(refund_id, with_back)` | Tombol keputusan refund. |
| `_refund_text(refund_id, item)` | Ringkasan satu permintaan refund untuk staf. |
| `_notify_staff(bot, refund_id, item)` | Kirim permintaan refund baru ke semua staf. |
| `pending_refunds_menu(query)` | Antrian refund yang belum dibayar. |
| `refund_callback(query, context)` | Tombol refund:view/paid/cancel. |

### `handlers/handler_saldo_cek.py`

| Fungsi | Keterangan |
|---|---|
| `cek_saldo(update, context)` | /saldo: saldo user + tombol Isi Saldo. |

### `handlers/handler_server.py`
Server Saya: add/edit wizard (buttons). /addserver etc. open the same flow.

| Fungsi | Keterangan |
|---|---|
| `server_limit_reached(user_id)` | Return (reached, used, limit) for the user's saved servers. |
| `_limit_text(used, limit)` | Teks peringatan batas server. |
| `start_server_wizard(query, context)` | Start a sequential server form from an inline button or /addserver. |
| `start_edit_server_wizard(query, context, index)` | Edit a saved server through the same safe, password-deleting wizard. |
| `handle_server_wizard(update, context)` | Consume form input. Password messages are removed immediately. |
| `_test_and_store(update, context, wizard, waiting)` | Uji koneksi router dari form, lalu simpan (berhasil) atau tawarkan isi ulang / simpan tanpa cek. |
| `_delete_quietly(message)` | Hapus pesan ⏳ tanpa error. |
| `_store_server(user_id, wizard)` | Save the wizard's server; return (text, keyboard factory). |
| `_store_server_locked(user_id, wizard)` | Isi _store_server (DATA_LOCK dipegang). |
| `force_save_server(query, context)` | Tombol 💾 Simpan Tanpa Cek: simpan server yang gagal diuji (router sedang offline). |

### `handlers/handler_start.py`

| Fungsi | Keterangan |
|---|---|
| `start_command_handler(update, context)` | /testppp: cek PPPoE pada sesi router aktif. |
| `start_command_handler_by_custom(update, context)` | /custom: mulai form Server Custom. |
| `begin_custom_server(context, user_id, message)` | Start a temporary server session; it is never written to datauser.json. |
| `handle_custom_server_input(update, context)` | Consume temporary server credentials and delete the password message. |
| `_test_custom_server(update, context, wizard, password, waiting)` | Uji koneksi Server Custom; berhasil → jadikan sesi aktif. |
| `run_pppoe_test(context, user_id, chat_id, user_data)` | Run the PPPoE test from either a command or an inline callback. |
| `_delete_quietly(bot, message)` | Hapus pesan tanpa error (untuk pesan ⏳). |

### `handlers/handler_traffic.py`

| Fungsi | Keterangan |
|---|---|
| `monitoring_command_handler(update, context)` | /traffic: kirim grafik untuk interface yang sudah dipilih lewat tombol. |
| `run_traffic_monitoring(context, user_id, chat_id, user_data)` | Fetch the RouterOS graph first; charge only when the image was retrieved. |
| `_stored_server_index(user_id, session)` | Index Server Saya yang sedang dipakai sesi (cocok nama + alamat), atau None. |
| `begin_www_port(query, context, index)` | Tombol 🌐 Atur Port Web: form port service www untuk grafik (index = Server Saya, None = sesi aktif). |
| `handle_www_port_input(update, context)` | Form port web: simpan ke Server Saya (bila tersimpan) dan ke sesi aktif. |
| `retry_traffic(query, context)` | Tombol 🔁 Coba Lagi: ambil ulang grafik interface terakhir. |

### `handlers/handler_transaction.py`
Transaction history for the user's own account (/historybulanan, /historytahunan, 📜 buttons).

Konstanta: `MONTHS`

| Fungsi | Keterangan |
|---|---|
| `_year_from(context)` | Tahun dari argumen command, default tahun ini; None bila tidak valid. |
| `check_monthly_transactions(update, context)` | /historybulanan dan tombol 📜: riwayat per bulan milik user. |
| `check_yearly_transactions(update, context)` | /historytahunan dan tombol 📜: total setahun milik user. |

### `handlers/handler_user.py`
User management for staff: active/archived lists, balances, archive/activate.

| Fungsi | Keterangan |
|---|---|
| `users_menu(query)` | Menu 👥 Data User. |
| `users_callback(update, context)` | Tombol users:* (aktif, arsip, saldo). |
| `_delete_user(query, context, target_id)` | Tombol users:delete:<id> (superadmin): hapus akun, beri tahu user beserta refund. |
| `set_user_active(target_id, active)` | Archive/activate one user. Returns a message; raises ValueError if not found. |
| `_toggle_command(update, context, active)` | Dasar /arsipkan dan /aktifkan. |
| `arsipkan_user(update, context)` | /arsipkan <user_id>. |
| `aktifkan_user(update, context)` | /aktifkan <user_id>. |
| `_user_line(uid, record)` | Satu baris ringkasan user (ID, nama, saldo, server). |
| `_send_list(update, context, title, lines, empty)` | Kirim daftar user ke staf (dengan tombol kembali). |
| `user_aktif(update, context)` | /useraktif dan tombol 👥 User Aktif. |
| `user_arsip(update, context)` | /userarsip dan tombol 📦 User Arsip. |
| `cek_semua_saldo(update, context)` | /saldouser dan tombol 💰 Saldo User. |

### `handlers/handler_version.py`
/version: users see features they can use; staff also see backend/admin changes.

Konstanta: `USER_FEATURES`, `USER_UPDATES`, `ADMIN_UPDATES`

| Fungsi | Keterangan |
|---|---|
| `_version_tuple(text)` | '2.2.1 (Monitoring ...)' -> (2, 2, 1); unknown -> (0,). |
| `_is_released(version)` | True bila versi ≤ APP_VERSION di .env (sudah dirilis). |
| `_format_updates(updates, limit, include_unreleased)` | Format daftar update; yang belum dirilis disembunyikan kecuali include_unreleased. |
| `version_text(admin_view)` | Isi /version: versi user (fitur & update terlihat) atau versi admin (catatan rilis). |
| `version_command_handler(update, context)` | /version dan tombol 🆕 Versi. |

### `handlers/handler_wallet.py`
Wallet request and staff approval flow, including photo proof metadata.

| Fungsi | Keterangan |
|---|---|
| `user_label(user_id)` | 'Nama (ID 123)' using the name recorded at registration. |
| `wallet_menu(update, context)` | Menu 💳 Saldo: saldo, paket nominal (QRIS statik), nominal bebas, riwayat. |
| `_send_qris(context, chat_id, qris_file_id, amount, query)` | Tampilkan QRIS + instruksi bayar, lalu tunggu foto bukti transfer. |
| `wallet_callback(query, context)` | Tombol wallet:amount:N (paket) dan wallet:custom (nominal bebas). |
| `handle_topup_custom_input(update, context)` | Form ✍️ Nominal Lain: validasi nominal lalu tampilkan QRIS umum. True bila dipakai. |
| `_save_uploaded_qris(target, file_id)` | Simpan foto QRIS dari superadmin sesuai target upload. Mengembalikan (teks, keyboard). |
| `capture_payment_proof(update, context)` | Foto masuk: QRIS baru (superadmin) atau bukti transfer → antrian topup. |
| `packages_menu(query)` | Menu admin 💳 Paket Saldo & QRIS: daftar paket, tambah, QRIS nominal bebas. |
| `package_callback(query, context, action)` | Tombol admin:pkg:<view/show/qris/delask/del>:<nominal>. |
| `begin_qris_upload(query, context)` | Tombol 🖼 QRIS Nominal Bebas (superadmin): foto berikutnya menjadi QRIS umum. |
| `topup_approval_callback(query, context)` | Tombol topup:approve/reject: tambah saldo user atau tolak. |
| `pending_topups_menu(query)` | Persistent queue view: approvals remain available after notifications scroll away. |
| `topup_queue_callback(query, context)` | Detail satu permintaan topup di antrian. |
| `begin_manual_topup(query, context)` | Mulai form ➕ Tambah Saldo manual (staf). |
| `handle_manual_topup_input(update, context)` | Consume admin's two-step manual credit input. Return True if consumed. |
| `set_qris_command(update, context)` | /setqris: superadmin mengirim foto QRIS berikutnya. |

### `handlers/handler_warning.py`

| Fungsi | Keterangan |
|---|---|
| `warning(update, context)` | /why: arti ⚠️ Tahap 1 dan 🚨 Tahap 2 dengan nilai milik user. |

### `handlers/send_startup_message.py`

Konstanta: `APP_VERSION`, `APP_NAME`

| Fungsi | Keterangan |
|---|---|
| `send_startup_message(context)` | Saat bot start: perbarui versi di app_info.json dan kabari user aktif. |
| `clear_reply_interface(bot, chat_ids)` | One-time cleanup of the "Reply to <bot>" bar left by old ForceReply prompts. |

## models/ — sesi di memori

### `models/userdata.py`
Sesi router yang sedang dipakai tiap user (hanya di memori, hilang saat bot restart).

| Fungsi | Keterangan |
|---|---|
| class `UserData` | Router aktif satu user: Server Saya yang dipilih atau Server Custom. |
