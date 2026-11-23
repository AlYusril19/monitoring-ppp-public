"""/version: users see features they can use; staff also see backend/admin changes.

Add work-in-progress entries at the TOP of both lists while developing:
  USER_UPDATES  — only what a customer sees or can do (buttons, messages, costs).
  ADMIN_UPDATES — admin features and backend fixes.
Entries newer than APP_VERSION in .env are treated as unreleased: hidden from
users, labelled "belum dirilis" for admins. Releasing = raising APP_VERSION.
Keep it in sync with CHANGELOG.md.
"""
import os
import re

from dotenv import load_dotenv

from configs.navigation import home_keyboard

load_dotenv()

USER_FEATURES = [
    "Dashboard tombol: Server Saya, Server Custom, Monitor PPPoE, Monitor Traffic, Saldo, Monitoring",
    "Simpan beberapa router; password otomatis dihapus dari chat",
    "Cek pelanggan PPPoE yang down beserta namanya",
    "Grafik traffic interface dari Tools > Graphing",
    "Notifikasi otomatis 2 tahap (⚠️ / 🚨) yang bisa Anda atur sendiri",
    "Isi saldo lewat QRIS dan lihat riwayat transaksi",
]

USER_UPDATES = [
    ("2.3.0", [
        "⚡ Bot lebih cepat & responsif; cek router yang lambat tidak lagi membuat bot macet",
        "Alamat router bisa DDNS/hostname dan port API lain (contoh router.ddns.net:8000)",
        "Koneksi gagal? Bot cek ping untuk menunjukkan apakah masalahnya di IP atau di port/API",
        "📈 Traffic: atur 🌐 Port Web bila port www router bukan 80, plus panduan bila Tools > Graphing kosong",
        "Router mati / login salah: pesan jelas (bukan \"timed out\") dan saldo tidak dipotong",
        "Tambah server menguji koneksi dulu sebelum disimpan",
        "💳 Saldo: pilih paket dengan QRIS masing-masing, atau ✍️ Nominal Lain sesuai kebutuhan",
        "🌙 Jam Senyap di ⚙️ Monitoring: tidak ada notifikasi & potongan saldo di jam yang Anda pilih (format 24 jam)",
        "Hapus akun menampilkan rincian refund saldo sesuai kebijakan",
        "Registrasi lebih aman dengan tombol 📱 Kirim Nomor Saya",
        "Notifikasi otomatis 2 tahap: ⚠️ memicu notifikasi, 🚨 mengirim eskalasi tanpa biaya tambahan selama jeda alert",
        "Monitor PPPoE manual selalu menampilkan semua pelanggan yang down",
        "Riwayat transaksi bulanan/tahunan di menu Saldo",
        "Server Saya menampilkan jumlah server dan batasnya",
        "/cancel untuk membatalkan isian apa pun",
        "Chat lebih rapi: balasan bot terhapus otomatis, hasil monitoring tetap tersimpan",
        "Tombol 🗑 Bersihkan semua chat di menu 🧹 Chat",
        "Daftar pelanggan down yang sangat banyak dikirim sebagai file .txt, tidak lagi gagal terkirim",
        "Grafik traffic yang gagal diambil tidak memotong saldo",
        "/info berisi panduan penggunaan; tombol 💸 Biaya menampilkan rincian biaya",
    ]),
    ("2.2.1", [
        "Atur ambang Warning dan profile PPPoE yang dikecualikan",
        "Tombol Kelola untuk edit/hapus server",
    ]),
]

ADMIN_UPDATES = [
    ("2.3.0", [
        "Performa: connection pool 16, hapus pesan & log admin di latar belakang, kerja router via in_background, "
        "job monitoring paralel per user, DATA_LOCK + tulis JSON atomik",
        "Alamat server: host:port (split_host_port), diagnosa ping (diagnose_address), servers[].www_port",
        "Koneksi router: RouterError + klasifikasi alasan; get_down_users tidak lagi mengembalikan [] saat putus",
        "💳 Paket & QRIS: paket nominal + QRIS statik (tambah/ubah/hapus), QRIS & batas nominal bebas",
        "💸 Refund: % kebijakan, 🗑 Hapus User dengan rincian refund, 💸 Antrian Refund",
        "🎁 Trial & Registrasi: nominal, mode manual/otomatis/nonaktif, batas pengajuan per jam, jeda setelah ditolak",
        "Anti akun massal: nomor wajib kontak Telegram sendiri, 1 trial per nomor & per akun",
        "Keamanan: cek akses admin terpusat untuk tombol & command, percobaan akses dicatat di log",
        "Menu ⚙️ Harga & Role berbasis tombol: harga, saldo trial, batas server (default 5), nominal topup, profile global, role",
        "Menu 👥 Data User: aktif, arsip, saldo, arsipkan/aktifkan",
        "Topup & saldo manual menampilkan nama + ID user; saldo manual tercatat di log admin",
        "Command lama (/addserver, /connect, /daftar, /topup, ...) membuka menu tombol yang sama",
        "User arsip tidak dipantau dan tidak dipotong biaya",
        "Perbaikan: biaya notifikasi sebelumnya tidak tercatat; kini terpotong dan masuk laporan",
        "Perbaikan: ganti versi tidak lagi menghapus pengaturan & antrian",
        "Perbaikan: nama dengan _ atau * tidak lagi menggagalkan pesan",
        "User Testing identik dengan dashboard user",
        "/info dan /version dibedakan untuk admin dan user",
    ]),
    ("2.2.1", [
        "Threshold notifikasi, Warning ⚠️/🚨, kelola server, dokumentasi pengembangan",
    ]),
]


def _version_tuple(text):
    """'2.2.1 (Monitoring ...)' -> (2, 2, 1); unknown -> (0,)."""
    match = re.search(r"\d+(?:\.\d+)*", str(text or ""))
    return tuple(int(part) for part in match.group(0).split(".")) if match else (0,)


def _is_released(version):
    """True bila versi ≤ APP_VERSION di .env (sudah dirilis)."""
    return _version_tuple(version) <= _version_tuple(os.environ.get("APP_VERSION"))


def _format_updates(updates, limit=2, include_unreleased=False):
    """Format daftar update; yang belum dirilis disembunyikan kecuali include_unreleased."""
    blocks = []
    for version, items in updates:
        released = _is_released(version)
        if not released and not include_unreleased:
            continue
        label = f"Update {version}" + ("" if released else " (dalam pengembangan, belum dirilis)")
        blocks.append(label + "\n" + "\n".join(f"   - {item}" for item in items))
        if len(blocks) >= limit:
            break
    return "\n\n".join(blocks) or "Belum ada catatan update."


def version_text(admin_view):
    """Isi /version: versi user (fitur & update terlihat) atau versi admin (catatan rilis)."""
    app_version = os.environ.get('APP_VERSION', '-')
    released = os.environ.get('RELEASED', '-')
    email = os.environ.get('EMAIL', '')
    header = f"Bot Version {app_version} (Released in {released})"
    if admin_view:
        return (f"{header}\n🛡 Catatan rilis admin\n\n{_format_updates(ADMIN_UPDATES, include_unreleased=True)}\n\n"
                f"Yang dilihat pengguna:\n{_format_updates(USER_UPDATES, limit=1, include_unreleased=True)}\n\n"
                f"Develop by SkyTaMa {email}")
    features = "\n".join(f"   - {item}" for item in USER_FEATURES)
    return (f"{header}\n\nFitur yang bisa Anda gunakan\n{features}\n\n"
            f"{_format_updates(USER_UPDATES)}\n\nDevelop by SkyTaMa {email}")


def version_command_handler(update, context):
    """/version dan tombol 🆕 Versi."""
    from handlers.handler_info import is_admin_view
    update.effective_message.reply_text(
        version_text(is_admin_view(update.effective_user.id, context)), reply_markup=home_keyboard())
