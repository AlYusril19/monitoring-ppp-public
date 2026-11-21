from configs.send_message import allowed_admin_ids, send_message
from configs.data_json_user import load_user_data
import os
from dotenv import load_dotenv
from configs.app_settings import get_monitoring_config, get_price
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

    if str(user_id) not in user_data and user_id not in allowed_admin_ids:
        update.message.reply_text("Anda belum terdaftar, silahkan /daftar terlebih dahulu.")
        return
    
    message1 = "Berikut adalah command menjalankan monitoring server\n\n" \
            "/addserver `menambahkan data server`\n" \
            "/delserver `menghapus data server`\n" \
            "/listserver `menampilkan list server`\n" \
            "/editserver `menampilkan list server`\n" \
            "/connect `menghubungkan ke server`\n" \
            "/infonotify `informasi pesan otomatis`\n" \
            "/custom `menghubungkan ke server dengan custom IP`\n" \
            "/menu `membuka menu tombol`\n" \
            "/monitoring `mengatur interval monitoring`"
            
    message2 = "Berikut adalah command lain\n\n" \
            "/saldo `cek saldo`\n" \
            "/biaya `cek biaya per transaksi`\n" \
            "/info `Info Command Bot`\n" \
            "/version `Versi Bot`"
            
    message3 = "Jika muncul pesan kendala (error) silahkan /exit\n" \
            "Gunakan user *READ* untuk keamanan data anda terimakasih!\n\n" \
            f"{app_name} {app_version}"
            
    messageadmin1 = "Berikut command untuk admin \n"\
        "/saldouser `untuk melihat saldo user`\n"\
        "/topup `untuk topup saldo user`\n"\
        "/aktifkan `untuk aktifkan user`\n"\
        "/arsipkan `untuk arsipak user`\n"\
        "/useraktif `untuk melihat user aktif`\n"\
        "/userarsip `untuk melihat user arsip`\n"\
        "/laporanbulanan `untuk melihat laporan saldo bulanan`\n"\
        "/laporantahunan `untuk melihat laporan saldo tahunan`\n"\
        
            
    send_message(bot, chat_id, message1)
    send_message(bot, chat_id, message2)
    if user_id in allowed_admin_ids:
        send_message(bot, chat_id, messageadmin1)
    send_message(bot, chat_id, message3)

def notify_command_handler(update, context):
    user_id = str(update.effective_user.id)
    bot = context.bot
    chat_id = update.effective_chat.id
    user_data = load_user_data()

    if user_id not in user_data and update.effective_user.id not in allowed_admin_ids:
        update.message.reply_text("Anda belum terdaftar, silahkan /daftar terlebih dahulu.")
        return
    
    config = get_monitoring_config(user_data[user_id])
    message = (
        "*Monitoring PPPoE Otomatis*\n\n"
        "Syarat:\n"
        "- Simpan minimal satu server melalui *Server Saya*.\n"
        "- RouterOS API harus aktif dan gunakan akun READ.\n"
        "- Server Custom hanya untuk sesi manual; monitoring otomatis memakai server tersimpan.\n\n"
        "Cara kerja:\n"
        f"- Interval normal: *{config['normal_interval_minutes']} menit*.\n"
        f"- Setelah ditemukan user down: *{config['alert_interval_minutes']} menit*.\n"
        "- Notifikasi pertama saat down dipotong sesuai harga notifikasi.\n"
        "- Saat status pulih, bot mengirim notifikasi recovery dan kembali ke interval normal.\n"
        "- Jika saldo tidak cukup, monitoring dijeda sampai Anda melanjutkan dari menu Monitoring.\n\n"
        f"Biaya notifikasi saat ini: *Rp{get_price('notify'):,}*.\n"
        "Atur interval, jeda, atau lanjutkan lewat tombol *Monitoring* di Dashboard."
    )
    update.effective_message.reply_text(message, parse_mode="Markdown", reply_markup=home_keyboard())
