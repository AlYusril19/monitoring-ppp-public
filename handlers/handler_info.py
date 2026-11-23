"""/info and /infonotify texts.

Two audiences:
  * user  — how to use the bot, what each action costs, own account status;
  * admin — how to run the service, current settings, admin commands.
An admin in User Testing mode sees the user version, exactly like a customer.
"""
import os

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from configs.app_settings import get_monitoring_config, get_price, get_server_limit, is_staff, quiet_hours_label
from configs.data_json_user import load_user_data
from configs.format_rupiah import format_rupiah
from configs.navigation import home_keyboard
from configs.send_message import escape_md

load_dotenv()


def is_admin_view(user_id, context):
    """Staff see admin texts, except while testing the customer view."""
    return is_staff(user_id) and not context.user_data.get("user_testing_mode")


def info_keyboard():
    """Tombol di bawah /info: Biaya, Info Notify, Versi, Dashboard."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💸 Biaya", callback_data="menu:biaya"),
         InlineKeyboardButton("🔔 Info Notify", callback_data="menu:notify"),
         InlineKeyboardButton("🆕 Versi", callback_data="menu:version")],
        [InlineKeyboardButton("🏠 Dashboard", callback_data="nav:home")],
    ])


def _footer():
    """Nama aplikasi + versi dari .env."""
    return f"{os.environ.get('APP_NAME', '')} {os.environ.get('APP_VERSION', '')}".strip()


# ---------------------------------------------------------------- user
def user_info_messages(user_id, record):
    """Isi /info untuk user: akun, cara menggunakan, perintah cepat."""
    servers = len(record.get("servers", []))
    status = "dijeda ⏸" if record.get("monitoring_state", {}).get("paused") else "aktif ▶"
    akun = (
        "👤 *Akun Anda*\n"
        f"Saldo: *{format_rupiah(record.get('saldo', 0))}*\n"
        f"Server tersimpan: *{servers}/{get_server_limit(user_id)}*\n"
        f"Monitoring otomatis: *{status}*")
    panduan = (
        "📘 *Cara Menggunakan*\n\n"
        "*1. Hubungkan router*\n"
        "🖥 *Server Saya* → ➕ Tambah server → isi nama, IP/hostname/DDNS, username, password. "
        "Port API bukan 8728? Tulis `host:port`, mis. `router.ddns.net:8000`. "
        "Koneksi diuji dulu sebelum disimpan; password otomatis dihapus dari chat. "
        "Gunakan akun RouterOS *read-only* dan aktifkan IP > Services > *api*.\n"
        "🔧 *Server Custom* untuk router sementara (tidak disimpan, tidak dipantau otomatis).\n\n"
        "*2. Cek pelanggan PPPoE*\n"
        "📡 *Monitor PPPoE* → pilih server → bot menampilkan semua pelanggan yang down.\n\n"
        "*3. Lihat grafik traffic*\n"
        "📈 *Monitor Traffic* → pilih server → pilih interface (yang aktif di Tools > Graphing). "
        "Graphing masih kosong? Bot menampilkan panduan mengaktifkannya. "
        "Port www router bukan 80? Atur di ⚙️ Kelola → 🌐 Port Web.\n\n"
        "*4. Monitoring otomatis*\n"
        "Semua server di Server Saya dicek otomatis. Atur di ⚙️ *Monitoring*: "
        "cek tiap berapa menit, ⚠️ Tahap 1, 🚨 Tahap 2, jeda alert, profile yang dikecualikan, dan "
        "🌙 jam senyap (mis. 22:00-06:00: tanpa cek, notifikasi, & biaya). Detail: 🔔 *Info Notify*.\n\n"
        "*5. Router gagal terhubung?*\n"
        "Bot menjelaskan penyebabnya (login salah, router tidak merespons, API mati, alamat salah) dan "
        "mengecek ping: membalas = IP benar, masalah di port/API; tidak membalas = router mati/IP salah. "
        "Saldo *tidak dipotong* bila router gagal dihubungi.\n\n"
        "*6. Isi saldo*\n"
        "💳 *Saldo* → pilih paket atau ✍️ Nominal Lain → scan QRIS → kirim foto bukti transfer → "
        "tunggu persetujuan admin. Riwayat transaksi ada di menu yang sama.\n\n"
        "*7. Hapus akun*\n"
        "🗑 *Hapus Akun* menampilkan rincian refund dulu (saldo trial tidak direfund, % sesuai kebijakan) "
        "sebelum Anda konfirmasi.\n\n"
        "Batalkan isian apa pun dengan /cancel atau tombol ✖️ Batal.\n\n"
        "Rincian biaya: tekan tombol 💸 *Biaya* di bawah.")
    perintah = (
        "⌨️ *Perintah cepat* (semua juga tersedia sebagai tombol)\n"
        "/menu · /saldo · /topup · /biaya · /monitoring · /why · /infonotify · /version · /cancel\n\n"
        f"{_footer()}")
    return [akun, panduan, perintah]


# ---------------------------------------------------------------- admin
def admin_info_messages(user_id):
    """Isi /info untuk staf: panduan admin, pengaturan, biaya & pendapatan, command."""
    from handlers.handler_admin_settings import settings_text
    panduan = (
        "🛡 *Panduan Admin*\n\n"
        "*Registrasi* — 📥 *Antrian Registrasi*: pilih ✅ Setujui (+ Trial bila layak) atau ❌ Tolak. "
        "Nomor diverifikasi lewat kontak Telegram; ⚠️ = nomor/akun sudah pernah trial atau dipakai akun lain. "
        "Atur trial & batas pengajuan di 👥 Data User → 🎁 Trial & Registrasi.\n\n"
        "*Topup* — ⏳ *Antrian Topup*: cek foto bukti (paket atau nominal bebas), lalu Setujui/Tolak. "
        "➕ *Tambah Saldo* untuk saldo manual tanpa bukti.\n\n"
        "*User* — 👥 *Data User*: daftar aktif/arsip, saldo, arsipkan (monitoring otomatis berhenti), aktifkan, "
        "🗑 hapus user (superadmin, rincian refund tampil dulu). 💸 *Antrian Refund*: bayar di luar bot, "
        "lalu tandai ✅ Sudah Dibayar (user diberi tahu) atau ❌ Batalkan.\n\n"
        "*Pengaturan* — ⚙️ *Harga & Role* (superadmin): harga, % refund, batas server, "
        "profile PPPoE global, role admin/operator. 💳 *Paket & QRIS*: tambah paket (nominal → foto QRIS), "
        "ganti QRIS/nominal, hapus paket, QRIS & batas nominal bebas.\n\n"
        "*Keamanan* — tombol & command admin dicek terpusat; percobaan akses oleh user biasa dicatat di chat log. "
        "Satu trial per nomor HP & per akun Telegram.\n\n"
        "*Laporan* — 📊/📈 pendapatan bulanan/tahunan.\n\n"
        "*Uji tampilan user* — 🧪 *User Testing* membuka dashboard user asli; kembali lewat 🛡 Kembali ke Dashboard Admin.")
    biaya = (
        "💰 *Biaya & Pendapatan*\n\n"
        "• Akun staf (superadmin/admin/operator) tidak dipotong biaya.\n"
        "• Notifikasi otomatis user dipotong saat ⚠️ Tahap 1 dan setiap pengingat setelah jeda alert; "
        "eskalasi 🚨 gratis.\n"
        "• Tidak ada potongan bila router gagal dihubungi atau grafik gagal diambil, dan selama 🌙 jam senyap user.\n"
        "• Laporan: *saldo masuk* = topup QRIS + saldo manual; *pemakaian* = PPPoE, traffic, notifikasi.\n"
        "• Saldo trial tidak dihitung sebagai pendapatan dan tidak direfund.")
    perintah = (
        "⌨️ *Command admin* (semua juga tersedia sebagai tombol)\n"
        "/daftar — antrian registrasi\n"
        "/topup — tambah saldo manual\n"
        "/useraktif · /userarsip · /saldouser — data user\n"
        "/arsipkan <id> · /aktifkan <id> — status user\n"
        "/laporanbulanan <bulan> · /laporantahunan <tahun>\n"
        "/settings — ringkasan pengaturan (khusus staf)\n"
        "/setprice · /settrial · /setmaxserver · /setrole · /setqris\n"
        "Paket & QRIS, trial & registrasi, % refund, hapus user: lewat tombol di dashboard admin.\n\n"
        f"{_footer()}")
    return [panduan, settings_text(user_id), biaya, perintah]


# ---------------------------------------------------------------- handlers
def infolengkap_command_handler(update, context):
    """/info dan tombol ℹ️ Info (isi sesuai peran)."""
    user_id = update.effective_user.id
    record = load_user_data().get(str(user_id))
    if is_admin_view(user_id, context):
        messages = admin_info_messages(user_id)
    elif record:
        messages = user_info_messages(user_id, record)
    else:
        update.effective_message.reply_text("Anda belum terdaftar, silahkan /start untuk mengajukan registrasi.",
                                            reply_markup=home_keyboard())
        return
    chat_id = update.effective_chat.id
    for index, text in enumerate(messages):
        markup = info_keyboard() if index == len(messages) - 1 else None
        context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown", reply_markup=markup)


def notify_command_handler(update, context):
    """/infonotify: penjelasan monitoring otomatis dengan nilai milik user."""
    user_id = str(update.effective_user.id)
    user_data = load_user_data()

    if user_id not in user_data and not is_staff(update.effective_user.id):
        update.effective_message.reply_text("Anda belum terdaftar, silahkan /start untuk mengajukan registrasi.",
                                            reply_markup=home_keyboard())
        return

    config = get_monitoring_config(user_data.get(user_id, {}))
    profiles = escape_md(", ".join(config["excluded_profiles"])) or "tidak ada"
    message = (
        "*Monitoring PPPoE Otomatis*\n\n"
        "Syarat:\n"
        "- Simpan minimal satu server melalui *Server Saya* (IP, hostname, atau DDNS; port API lain: `host:port`).\n"
        "- RouterOS API (IP > Services > api) harus aktif dan gunakan akun READ.\n"
        "- Server Custom hanya untuk sesi manual; monitoring otomatis memakai server tersimpan.\n\n"
        "Cara kerja:\n"
        f"- Router dicek setiap *{config['normal_interval_minutes']} menit*.\n"
        f"- ⚠️ Tahap 1: *≥ {config['warning_threshold']} pelanggan down* → notifikasi otomatis (dipotong biaya).\n"
        f"- 🚨 Tahap 2: *≥ {config['critical_threshold']} pelanggan down* → notifikasi eskalasi, gratis selama jeda alert.\n"
        f"- Jeda alert *{config['alert_interval_minutes']} menit*: bila masih down setelah itu, notifikasi diulang dan dipotong lagi.\n"
        f"- Profile dikecualikan: *{profiles}*.\n"
        f"- 🌙 Jam senyap: *{quiet_hours_label(config['quiet_hours'])}*. Selama jam itu tidak ada cek, "
        "notifikasi, maupun potongan saldo.\n"
        "- Saat status pulih, bot mengirim notifikasi recovery.\n"
        "- Router mati / tidak dapat dihubungi: bot memberi tahu *sekali* beserta penyebabnya, lalu memberi tahu "
        "lagi saat terhubung kembali. *Tidak dipotong biaya.*\n"
        "- Jika saldo tidak cukup, monitoring dijeda sampai Anda melanjutkan dari menu Monitoring.\n\n"
        f"Biaya notifikasi saat ini: *Rp{get_price('notify'):,}*.\n"
        "Atur interval, ambang, jam senyap, atau lanjutkan lewat tombol ⚙️ *Monitoring*."
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚙️ Monitoring", callback_data="menu:monitor"),
         InlineKeyboardButton("💸 Cek Biaya", callback_data="menu:biaya")],
        [InlineKeyboardButton("🏠 Dashboard", callback_data="nav:home")],
    ])
    update.effective_message.reply_text(message, parse_mode="Markdown", reply_markup=keyboard)
