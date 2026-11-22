from configs.send_message import allowed_admin_ids, send_message
from configs.data_json_user import load_user_data
import os
from dotenv import load_dotenv
from configs.app_settings import get_monitoring_config, get_price, is_staff
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from configs.navigation import home_keyboard
load_dotenv()

def info_command_handler(update, context):
    username_telegram = update.effective_user.username #username pengguna telegram
    message = f"Selamat datang, {username_telegram} ini adalah BOT Monitoring Jaringan Mikrotik by SkyTaMa\n\n" \
              "Silahkan tekan /info untuk informasi lebih lanjut\n"
    update.message.reply_text(message)

def infolengkap_command_handler(update, context):
    # user_id = str(update.effective_user.id)  # Mengonversi user_id ke string
    user_id = update.effective_user.id
    bot = context.bot
    chat_id = update.effective_chat.id
    user_data = load_user_data()
    app_version = os.environ.get('APP_VERSION')
    app_name = os.environ.get('APP_NAME')

    if str(user_id) not in user_data and not is_staff(user_id):
        update.effective_message.reply_text("Anda belum terdaftar, silahkan /start untuk mengajukan registrasi.")
        return
    
    message1 = "*Command lanjutan user*\n\n" \
            "/menu — dashboard tombol utama\n" \
            "/connect — hubungkan router tersimpan secara manual\n" \
            "/custom — login router sementara\n" \
            "/addserver, /editserver, /delserver, /listserver — kelola server via command\n" \
            "/testppp — tes PPPoE pada router yang sedang login\n" \
            "/traffic — cek traffic interface yang dipilih\n" \
            "/monitoring — interval, ambang notif, warning, dan profile pengecualian\n" \
            "/infonotify — penjelasan monitoring otomatis\n" \
            "/why — arti Warning ⚠️ dan 🚨"
            
    message2 = "*Command saldo dan sesi*\n\n" \
            "/saldo — cek saldo\n" \
            "/biaya — biaya tiap layanan\n" \
            "/exit — logout router sesi saat ini\n" \
            "/version — versi dan fitur bot"
            
    message3 = "Jika muncul pesan kendala (error) silahkan /exit\n" \
            "Gunakan user *READ* untuk keamanan data anda terimakasih!\n\n" \
            f"{app_name} {app_version}"
            
    messageadmin1 = "*Command lanjutan admin*\n"\
        "/saldouser, /useraktif, /userarsip — data pengguna\n"\
        "/aktifkan, /arsipkan — status akun\n"\
        "/laporanbulanan, /laporantahunan — pendapatan\n"\
        "/settings, /setprice, /settrial, /setrole, /setqris — konfigurasi admin\n"\
        "Antrian registrasi/topup dan tambah saldo manual tersedia di Dashboard Admin.\n"
        
            
    send_message(bot, chat_id, message1)
    send_message(bot, chat_id, message2)
    if is_staff(user_id):
        send_message(bot, chat_id, messageadmin1)
    send_message(bot, chat_id, message3)
    bot.send_message(chat_id=chat_id, text="Pilih aksi berikutnya:", reply_markup=home_keyboard())

def notify_command_handler(update, context):
    user_id = str(update.effective_user.id)
    bot = context.bot
    chat_id = update.effective_chat.id
    user_data = load_user_data()

    if user_id not in user_data and not is_staff(update.effective_user.id):
        update.effective_message.reply_text("Anda belum terdaftar, silahkan /start untuk mengajukan registrasi.")
        return
    
    config = get_monitoring_config(user_data.get(user_id, {}))
    message = (
        "*Monitoring PPPoE Otomatis*\n\n"
        "Syarat:\n"
        "- Simpan minimal satu server melalui *Server Saya*.\n"
        "- RouterOS API harus aktif dan gunakan akun READ.\n"
        "- Server Custom hanya untuk sesi manual; monitoring otomatis memakai server tersimpan.\n\n"
        "Cara kerja:\n"
        f"- Interval normal: *{config['normal_interval_minutes']} menit*.\n"
        f"- Setelah ditemukan user down: *{config['alert_interval_minutes']} menit*.\n"
        f"- Notifikasi hanya dikirim mulai *{config['notify_down_threshold']} pelanggan down*.\n"
        f"- Warning ⚠️ / 🚨 pada *{config['warning_threshold']}* / *{config['critical_threshold']} pelanggan down*.\n"
        f"- Profile dikecualikan: `{', '.join(config['excluded_profiles']) or 'tidak ada'}`.\n"
        "- Notifikasi pertama saat down dipotong sesuai harga notifikasi.\n"
        "- Saat status pulih, bot mengirim notifikasi recovery dan kembali ke interval normal.\n"
        "- Jika saldo tidak cukup, monitoring dijeda sampai Anda melanjutkan dari menu Monitoring.\n\n"
        f"Biaya notifikasi saat ini: *Rp{get_price('notify'):,}*.\n"
        "Atur interval, jeda, atau lanjutkan lewat tombol *Monitoring* di Dashboard."
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💸 Cek Biaya", callback_data="menu:biaya")],
        [InlineKeyboardButton("🏠 Dashboard", callback_data="nav:home")],
    ])
    update.effective_message.reply_text(message, parse_mode="Markdown", reply_markup=keyboard)
