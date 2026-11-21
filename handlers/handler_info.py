from configs.send_message import allowed_admin_ids, send_message
from configs.data_json_user import load_user_data
import os
from dotenv import load_dotenv
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
    user_id = str(update.effective_user.id)  # Mengonversi user_id ke string
    bot = context.bot
    chat_id = update.effective_chat.id
    user_data = load_user_data()

    if user_id not in user_data and update.effective_user.id not in allowed_admin_ids:
        update.message.reply_text("Anda belum terdaftar, silahkan /daftar terlebih dahulu.")
        return
    
    message = "*Fitur Notify digunakan untuk pengecekan client PPPOE secara otomatis*"
    message = "Berikut adalah syarat dan ketentuan menggunakan fitur ini."     
    message += "```Syarat"\
                "  - Pastikan anda sudah menyimpan data\n"\
                "    server menggunakan /addserver\n"\
                "  - Gunakan user READ untuk keamanan data\n"\
                "    anda\n"\
                "  - Pastikan services API anda sudah aktif\n"\
                "    dengan port default\n"\
                "  - Lakukan uji coba /connect ke server```"
    message += "```Ketentuan"\
                "  - Schedule pengecekan dilakukan setiap 30\n"\
                "    menit sekali selama 24jam nonstop\n"\
                "  - Cek pada log Mikrotik anda jika ada log\n"\
                "    login setiap 30 menit maka program\n"\
                "    sudah berjalan\n"\
                "  - Jika pesan notifikasi terkirim, maka\n "\
                "    pengecekan akan dilakukan kembali\n"\
                "    selama 4 jam kemudian\n" \
                "  - Jika pesan notifikasi terkirim >20:00\n"\
                "    maka pengecekan akan dilakukan kembali\n"\
                "    di jam 07:00```"
    
    send_message(bot, chat_id, message)
