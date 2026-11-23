# Command, Tombol, dan Alur Fitur

Prinsip: **satu fitur = satu implementasi.** Command membuka menu tombol yang sama, jadi aturan (batas server, hapus password, cek peran) hanya ditulis sekali.

Akses: **U** = user terdaftar · **S** = staf (superadmin/admin/operator) · **SA** = superadmin · **semua** = siapa saja.

## 1. Command

Didaftarkan di `main.py` (dict `COMMANDS`).

### User
| Command | Membuka / fungsi | Akses |
|---|---|---|
| `/start`, `/menu` | Dashboard sesuai peran; user baru → tombol ✨ Ajukan Registrasi | semua |
| `/cancel` | Batalkan form apa pun yang sedang terbuka | semua |
| `/listserver` `/connect` `/editserver` `/delserver` | Menu 🖥 Server Saya (pilih, ⚙️ Kelola → edit/hapus) | U |
| `/addserver` | Form tambah server (batas dicek, password dihapus) | U |
| `/custom` | Form Server Custom (sementara, tidak disimpan) | U |
| `/testppp` | Cek PPPoE pada router yang sedang dipilih | U |
| `/traffic` | Grafik interface yang sudah dipilih lewat tombol | U |
| `/monitoring` | Menu ⚙️ Monitoring pribadi | U |
| `/saldo` | Saldo + tombol Isi Saldo | U |
| `/topup` | Menu 💳 Saldo (paket / ✍️ nominal lain → QRIS → bukti) | U |
| `/historybulanan [tahun]` `/historytahunan [tahun]` | Riwayat transaksi sendiri | U |
| `/info` | Akun, cara menggunakan, perintah cepat (staf: versi admin) | U |
| `/biaya` | Rincian biaya (staf: daftar harga) | U |
| `/version` | Fitur & update yang terlihat user (staf: catatan rilis) | semua |
| `/why` `/infonotify` | Arti ⚠️/🚨 · cara kerja monitoring otomatis | U |
| `/exit` | Logout router (hapus sesi) | U |

### Admin
| Command | Membuka / fungsi | Akses |
|---|---|---|
| `/daftar` | 📥 Antrian registrasi | S |
| `/topup` | ➕ Form tambah saldo manual | S |
| `/useraktif` `/userarsip` `/saldouser` | Daftar user | S |
| `/arsipkan <id>` `/aktifkan <id>` | Arsip / aktifkan user | S |
| `/laporanbulanan [bulan]` `/laporantahunan [tahun]` | Laporan pendapatan | S |
| `/settings` | Ringkasan pengaturan | S |
| `/setprice <testppp\|traffic\|notify> <nominal>` | Harga fitur | SA |
| `/settrial <nominal>` | Saldo trial registrasi | SA |
| `/setmaxserver <jumlah>` | Batas server per user | SA |
| `/setrole <id> <operator\|admin\|user>` | Role | SA |
| `/setqris` | Ganti QRIS nominal bebas / cadangan (kirim foto berikutnya) | SA |

Semua `/set...` memakai `handler_admin_settings.apply_admin_input` — fungsi yang sama dengan tombol.

Command admin (`STAFF_COMMANDS` di `main.py`) dibungkus `configs/access.py::staff_only`: non-staf mendapat penolakan dan percobaannya dicatat ke chat log.

## 2. Tombol (`callback_data`)

Semua tombol masuk ke `handlers/handler_menu.py::menu_callback`. Batas Telegram: **64 byte** per `callback_data`.

**Akses dicek terpusat** sebelum routing (`configs/access.py::callback_allowed`): prefix `admin:` `users:` `reg:` `topup:` `refund:` hanya untuk staf (percobaan non-staf dicatat ke chat log, maks. 1×/10 menit per user); akun yang belum terdaftar hanya boleh `nav:home`, `onboard:register`, `input:cancel`. Handler tetap punya cek sendiri sebagai lapis kedua.

| Nilai / prefix | Diteruskan ke | Kegunaan |
|---|---|---|
| `nav:home` | `show_menu` | Dashboard (mode User Testing tetap aktif) |
| `nav:logout` | — | Hapus sesi router |
| `menu:servers` | `_show_servers` | 🖥 Server Saya (n/batas) |
| `menu:pppoe` | `run_pppoe_test` / `_prompt_server_before_pppoe` | 📡 Monitor PPPoE |
| `menu:traffic` · `tr:servers` · `tr:server:<i>` · `tr:iface:<srv>:<iface>` | `_show_traffic_servers`, `_show_interfaces`, `_run_traffic` | 📈 Monitor Traffic (`<srv>` = index atau `current`) |
| `tr:www` · `tr:www:<i>` · `tr:retry` | `handler_traffic.begin_www_port`, `retry_traffic` | 🌐 Port Web (sesi aktif / Server Saya ke-i) · 🔁 ambil ulang grafik |
| `menu:wallet` · `wallet:amount:<N>` · `wallet:custom` | `handler_wallet` | 💳 Saldo → paket (QRIS paket) / ✍️ Nominal Lain (QRIS umum) |
| `hist:monthly` · `hist:yearly` | `handler_transaction` | 📜 Riwayat (di menu Saldo) |
| `menu:monitor` · `mon:n:<m>` · `mon:a:<m>` · `mon:input:warning_threshold\|critical_threshold` · `mon:profiles` · `mon:quiet` · `mon:pause` · `mon:resume` | `handler_monitor_settings` | ⚙️ Monitoring: cek tiap, jeda alert, ⚠️/🚨, profile, 🌙 jam senyap, jeda/lanjut |
| `menu:info` · `menu:notify` · `menu:biaya` · `menu:version` | `handler_info`, `handler_biaya`, `handler_version` | Info, Info Notify, 💸 Biaya, 🆕 Versi |
| `menu:cleanup` · `clean:all` · `clean:<menit>` | `handler_menu`, `chat_tracker.clear_chat` | 🧹 Chat: 🗑 Bersihkan semua / hapus otomatis dashboard (0/60/1440) |
| `srv:add` · `srv:custom` · `srv:connect:<i>` · `srv:manage:<i>` · `srv:edit:<i>` · `srv:deleteask:<i>` · `srv:deleteconfirm:<i>` · `srv:forcesave` | `handler_menu`, `handler_server`, `handler_start` | Server Saya & Server Custom (`<i>` = index di `servers`) |
| `onboard:register` · `onboard:delete_confirm` · `onboard:delete_now` · `onboard:delete_cancel` | `handler_onboarding`, `handler_refund` | Registrasi & 🗑 Hapus Akun (dengan pemberitahuan refund) |
| `reg:view:<id>` · `reg:trial:<id>` · `reg:approve:<id>` · `reg:reject:<id>` | `handler_onboarding` | Antrian & keputusan registrasi |
| `topup:view:<id>` · `topup:approve:<id>` · `topup:reject:<id>` | `handler_wallet` | Antrian & keputusan topup |
| `admin:refunds` · `refund:view:<id>` · `refund:paid:<id>` · `refund:cancel:<id>` | `handler_refund` | 💸 Antrian Refund |
| `admin:pkg` · `admin:pkg:view\|show\|qris\|delask\|del:<N>` · `admin:qris` | `handler_wallet` | 💳 Paket & QRIS (`show:0` = QRIS nominal bebas) |
| `admin:trial` · `admin:trialmode:<manual\|auto\|off>` | `handler_admin_settings` | 🎁 Trial & Registrasi |
| `admin:testing` · `admin:exittesting` | `_admin_callback` | 🧪 User Testing masuk/keluar |
| `admin:registrations` · `admin:topups` · `admin:manualtopup` · `admin:manualcancel` · `admin:monthly` · `admin:yearly` | `_admin_callback` | Menu dashboard admin |
| `admin:settings` · `admin:set:<key>` | `handler_admin_settings` | ⚙️ Harga & Role dan formnya (§5) |
| `admin:users` · `users:active` · `users:archived` · `users:balances` · `users:delete:<id>` | `handler_user` | 👥 Data User (hapus user: superadmin) |
| `input:reset:<kind>` · `input:cancel` | `_input_wizard_callback` | ↩️ Reset form / ✖️ Batal **semua** form |

> Tombol baru: pakai prefix yang ada bila cocok. Prefix baru → cabang di `menu_callback` **dan** baris di tabel ini.

## 3. Aturan tampilan

### Tombol navigasi (`configs/navigation.py`)
| Jenis pesan | Tombol | Helper |
|---|---|---|
| Form (menunggu ketikan) | ✖️ Batal | `cancel_keyboard()` / `wizard_keyboard()` |
| Hasil di sub-menu | ⬅️ Kembali + 🏠 Dashboard | `back_keyboard(callback, label)` |
| Hasil akhir / error | 🏠 Dashboard | `home_keyboard()` / `send_message(..., with_dashboard=True)` |
| Saldo tidak cukup | 💳 Isi Saldo + 🏠 Dashboard | `topup_keyboard()` |
| Daftar pilihan | baris 🏠 Dashboard | `dashboard_row()` |
| Setelah hasil router | 📡 PPPoE · 📈 Traffic · 🏠 | `session_action_keyboard()` |

### Pesan sementara vs log (`configs/chat_tracker.py`)
| Tetap di chat (log) | Dihapus otomatis saat aksi berikutnya |
|---|---|
| Hasil Cek PPPoE (1 pesan; daftar panjang → `.txt`) | Menu, prompt form, konfirmasi, error, panel "Pilih aksi" |
| Grafik traffic (1 foto + keterangan) | Pesan ⏳ proses (dihapus begitu hasil keluar) |
| Notifikasi otomatis (down, eskalasi, pengingat, pulih, router tak terhubung) | Pesan startup "Bot telah direboot" |
| Pesan dari aksi admin (registrasi/topup disetujui, saldo manual), pesan ke staf | Ketikan user: command, isian form, foto bukti/QRIS |

🗑 **Bersihkan semua chat** menghapus keduanya (pesan tercatat ≤ 48 jam).

## 4. Alur utama

### Registrasi
```text
/start (user baru) → ✨ Ajukan Registrasi (onboard:register)
  → cek: masih pending? baru ditolak (< jeda)? batas pengajuan per jam penuh?
  → tombol 📱 Kirim Nomor Saya (reply keyboard request_contact) — nomor ketikan ditolak
  → handle_contact: kontak harus milik akun itu sendiri (contact.user_id == user)
  → app_info.registration_requests (pending, phone_verified, trial_block_reason) + notifikasi ke staf
  → staf: reg:trial | reg:approve | reg:reject   (juga dari 📥 Antrian / /daftar)
  → disetujui: record dibuat di datauser.json (+ transaksi trial_balance & trial_registry bila trial)
```
Trial (🎁 Trial & Registrasi di 👥 Data User): mode `manual` (tombol + Trial / Tanpa Trial), `auto` (✅ Setujui
selalu memberi trial bila layak), `off`. **Layak** = nomor & ID Telegram belum pernah menerima trial
(`app_info.trial_registry`, tidak ikut terhapus) dan nomor tidak dipakai akun lain. Kelayakan dicek ulang saat approval.

### Hapus akun & refund
```text
User: 🗑 Hapus Akun (onboard:delete_confirm) → pemberitahuan saldo, bagian trial, % refund, nominal refund
  → onboard:delete_now → handler_refund.delete_account
Admin (superadmin): 👥 Data User → 🗑 Hapus User → User ID → rincian refund → users:delete:<id> → user diberi tahu
delete_account: hapus record + sesi, topup pending → cancelled, refund > 0 → app_info.refund_requests + notifikasi staf + chat log
Staf: 💸 Antrian Refund → bayar di luar bot → refund:paid (user diberi tahu) | refund:cancel
```
Refund = (saldo − total trial yang pernah diterima, min 0) × `refund_percent` / 100. Saldo trial tidak pernah dibayar sebagai uang; akun staf tanpa refund.

### Server Saya
```text
menu:servers (/connect, /listserver) → "Server Saya (n/batas)"
  srv:add (/addserver) → cek batas → form nama → IP → username → password (dihapus)
    → ⏳ uji koneksi → berhasil: simpan (+ nama router)
    → gagal: pesan alasan, BELUM disimpan → 🔁 Isi Ulang | 💾 Simpan Tanpa Cek (srv:forcesave, tidak untuk login salah) | ✖️ Batal
  srv:manage:i → srv:edit:i (form sama) | srv:deleteask:i → srv:deleteconfirm:i
```
Batas: `app_settings.get_server_limit(user_id)` (default 5), dicek saat form dibuka **dan** saat menyimpan.
Alasan gagal koneksi diklasifikasikan di `mikrotik_function.classify_router_error` (login · timeout · refused · host · offline · other) dan dipakai juga oleh Server Custom & Monitor Traffic.
Alamat boleh IP, hostname, atau DDNS, dengan port API opsional `host:port` (default 8728; `split_host_port`, divalidasi `validate_address`). Bila gagal karena timeout/terputus, bot melakukan **ping** ke host (`diagnose_address`): membalas → IP benar, masalah di port API / service api / NAT / firewall; tidak membalas → router mati, internet putus, atau IP salah. `refused` = IP benar, port API tertutup. `login` = IP & port benar, username/password salah.

### Monitor PPPoE (manual)
```text
menu:pppoe → (belum ada sesi? pilih server: srv:connect:i)
  → ⏳ → login → get_down_users → (berhasil) charge_user("testppp")
  → gagal (login salah / timeout / API mati / alamat salah / putus di tengah): pesan alasan, saldo TIDAK dipotong
    login salah → sesi dihapus; lainnya → 🔁 Cek Lagi
  → 1 pesan log: server · waktu · SEMUA nama down (atau "UP semua") · label ⚠️/🚨 · biaya
```

### Monitor Traffic
```text
menu:traffic → tr:server:i → interface dari Tools > Graphing → tr:iface:...
  → ⏳ → ambil http://host[:www_port]/graphs/iface/<iface>/daily.gif → (berhasil) charge_user("traffic") → 1 foto log
  Graphing kosong → panduan konfigurasi (Winbox + perintah terminal)
  Grafik gagal → petunjuk (port www, service www, allow-address, tunggu ±5 menit) + 🌐 Atur Port Web (tr:www) · 🔁 Coba Lagi (tr:retry)
⚙️ Kelola server → 🌐 Port Web (tr:www:i) → form port → disimpan di servers[i].www_port
```
Grafik gagal diambil → saldo **tidak** dipotong. Port API di alamat (`host:8000`) tidak dipakai untuk grafik.

### Notifikasi otomatis (2 tahap)
| Kejadian | Pesan | Biaya |
|---|---|---|
| Down mencapai ⚠️ Tahap 1 | Notifikasi + nama | `notify` |
| Naik ke 🚨 Tahap 2 selama jeda alert | Eskalasi + nama | gratis |
| Sama/turun selama jeda | — | — |
| Jeda habis, masih ≥ ⚠️ | Pengingat + nama | `notify` |
| Turun di bawah ⚠️ | "Sudah pulih" | — |
| Router tidak terhubung (mati, timeout, login salah, API mati, putus di tengah cek) | "🚨 Server tidak dapat dihubungi" + alasan, sekali; lalu "kembali terhubung (sejak …)" | gratis |

Contoh (⚠️ 5, 🚨 10, jeda 120 menit): 5 down → Rp250; 10 down 40 menit kemudian → gratis; masih down setelah 120 menit → Rp250.

🌙 **Jam senyap** (per user, ⚙️ Monitoring, format 24 jam mis. `22:00-06:00`, boleh melewati tengah malam): selama jam itu user dilewati scheduler — tanpa cek router, tanpa pesan, tanpa potong saldo. Setelah jam senyap selesai, pengecekan berikutnya berjalan normal (notifikasi berbayar bila masih ≥ ⚠️ dan jeda alert sudah habis).

### Topup
```text
menu:wallet (/topup) → pilih paket (wallet:amount:N) → QRIS statik paket itu (cadangan: QRIS umum)
                     | ✍️ Nominal Lain (wallet:custom, hanya bila QRIS umum ada) → ketik nominal (min–max) → QRIS umum
  → kirim foto bukti → app_info.topup_requests (pending, source package|custom)
  → staf: topup:approve | topup:reject (tampil "nama (ID)")
Superadmin: 💳 Paket & QRIS → ➕ Tambah Paket (nominal → foto QRIS) · pilih paket → 👁 Lihat / 🖼 Ganti QRIS /
  ✏️ Ubah Nominal / 🗑 Hapus · 🖼 QRIS Nominal Bebas · ↔️ Batas Nominal
Staf: ➕ Tambah Saldo (/topup) → User ID → bot tampilkan nama & saldo → nominal
  → konfirmasi (nama, ID, nominal, saldo kini, admin) ke staf + chat log → transaksi manual_topup
```

### Info & versi per peran
`is_admin_view()` = staf **dan** tidak sedang User Testing.

| | User | Admin |
|---|---|---|
| `/info` | Akun Anda · Cara Menggunakan · Perintah cepat | Panduan Admin · Pengaturan · Biaya & Pendapatan · Command admin |
| 💸 Biaya | Harga, kapan dipotong, apa yang gratis (ambang milik user) | Daftar harga + catatan staf gratis |
| `/version` | Fitur yang bisa dipakai + `USER_UPDATES` yang sudah dirilis | `ADMIN_UPDATES` (termasuk yang belum dirilis, berlabel) |

Entri update dengan versi di atas `APP_VERSION` (.env) tersembunyi dari user.

### User Testing (admin)
```text
admin:testing → record uji (saldo 0) → dashboard user ASLI + 🛡 Kembali ke Dashboard Admin
admin:exittesting → Dashboard Admin
```
Perbedaan yang disengaja: admin tidak dipotong saldo.

## 5. Pengaturan admin (`admin:set:<key>`)

Di `handlers/handler_admin_settings.py` (`ADMIN_INPUTS` + `apply_admin_input`). Default di `configs/app_settings.py::DEFAULT_SETTINGS` dipakai bila admin belum pernah mengisi.

| Key | Tombol | Command | Default | Akses |
|---|---|---|---|---|
| `price:testppp` · `price:traffic` · `price:notify` | 💲 | `/setprice` | 125 · 50 · 250 | SA |
| `trial_balance` | 🎁 Nominal Trial (Data User → Trial) | `/settrial` | 5000 | SA |
| `reg_limit` | ⏱ Batas/Jam (Trial & Registrasi) | — | 10 pengajuan/jam | SA |
| `reg_cooldown` | ⏳ Jeda Ditolak (Trial & Registrasi) | — | 24 jam | SA |
| `refund_percent` | 💸 Refund % | — | 0 | SA |
| `max_servers` | 🖥 Batas Server | `/setmaxserver` | 5 | SA |
| `pkg_new` · `pkg_edit:<N>` | ➕ Tambah Paket · ✏️ Ubah Nominal (Paket & QRIS) | — | 5rb, 10rb, 25rb, 50rb, 100rb | SA |
| `custom_range` | ↔️ Batas Nominal | — | 10rb–1jt | SA |
| `delete_user` | 🗑 Hapus User (Data User) | — | — | SA |
| `excluded_profiles` | 👥 Profile Global | — | `expired`, `pribadi-home` | SA |
| `role` | 🛡 Atur Role | `/setrole` | — | SA |
| `archive` · `activate` | 📦 / ✅ di Data User | `/arsipkan` · `/aktifkan` | — | S |

## 6. Jenis transaksi

| `type` | Dibuat oleh | Tanda | Laporan admin |
|---|---|---|---|
| `testppp`, `traffic`, `notify` | `billing.charge_user` | − | Pemakaian |
| `topup_request` | approval topup QRIS | + | Saldo masuk |
| `manual_topup` | tambah saldo manual | + | Saldo masuk |
| `topup` | command lama (data historis) | + | Saldo masuk |
| `trial_balance` | registrasi dengan trial | + | **tidak dihitung** |
