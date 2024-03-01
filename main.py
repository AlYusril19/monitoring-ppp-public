from librouteros import connect
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from dotenv import load_dotenv
from mikrotik_function import get_name_server, get_down_users
from userdata import UserData
import os

load_dotenv()

user_data_dict = {}

telegram_bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
chat_user_ids = os.environ.get('ALLOWED_USER_IDS')

allowed_user_ids = set(map(int, chat_user_ids.split(',')))
bot = Bot(token=telegram_bot_token)

def start_command_handler(update, context):
    user_id = update.effective_user.id
    username_telegram = update.effective_user.username #username pengguna telegram


    if user_id not in allowed_user_ids:
        update.message.reply_text("Anda tidak diizinkan menggunakan bot ini.")
        return

    user_data = user_data_dict.get(user_id)

    if user_data is None:
        user_data = UserData()
        user_data_dict[user_id] = user_data

    if user_data.ip_address is None:
        # Jika IP belum diisi, kirim pertanyaan ke pengguna
        message = f"Selamat datang, *{username_telegram}*! Silakan masukkan IP MikroTik Anda:"
        update.message.reply_text(message)

    elif user_data.router_username is None:
        # Jika username belum diisi, kirim pertanyaan ke pengguna
        message = "Silakan masukkan username:"
        update.message.reply_text(message)

    elif user_data.router_password is None:
        # Jika password belum diisi, kirim pertanyaan ke pengguna
        message = "Silakan masukkan password:"
        update.message.reply_text(message)

    else:
        # Jika semua sudah diisi, lanjutkan dengan proses normal
        start_command_handler_after_input(update, context, user_data)

def start_command_handler_after_input(update, context, user_data):
    message = "Program Skytama Sudah Berjalan"
    bot = context.bot
    chat_id = update.effective_chat.id
    send_message(bot, chat_id, message)

    try:
        # Membuat koneksi ke MikroTik
        connection = connect(
            username=user_data.router_username,
            password=user_data.router_password,
            host=user_data.ip_address
        )

        nama_server = get_name_server(connection)

        # Cek apakah login berhasil
        if connection:
            print("Login berhasil!")
            print(f"Login ke server {nama_server}")
            # Kirim pesan telegram
            send_message(bot, chat_id, f"Login ke server *{nama_server}*")

            # Mendapatkan semua pengguna yang statusnya "down"
            down_users = get_down_users(connection)
            print(down_users)  # Tambahkan print statement untuk memeriksa down_users
            if down_users:
                down_users_message = "Client PPPOE status *DOWN*:\n"
                for username in down_users:
                    down_users_message += f"- {username} ❌ \n"
                send_message(bot, chat_id, down_users_message)
                send_message(bot,chat_id,"\n*Jika sudah selesai silahkan* /exit\n" \
                                "Gunakan /test untuk monitoring ulang")
            else:
                send_message(bot, chat_id, "User Status UP Semua 🤩")
        else:
            print("Login gagal!")
            send_message(bot, chat_id, "Login Gagal")
    except Exception as e:
        print("Terjadi kesalahan:", str(e))
        send_message(bot, chat_id, f"Terjadi kesalahan: {str(e)}")
        exit_command_handler(update, context)

def handle_input(update, context):
    user_id = update.effective_user.id
    user_data = user_data_dict.get(user_id)

    if user_data is None:
        user_data = UserData()
        user_data_dict[user_id] = user_data

    # Mendapatkan input dari pengguna
    if user_data.ip_address is None:
        user_data.ip_address = update.message.text.strip()
        message = "Silakan masukkan username:"
        update.message.reply_text(message)

    elif user_data.router_username is None:
        user_data.router_username = update.message.text.strip()
        message = "Silakan masukkan password:"
        update.message.reply_text(message)

    elif user_data.router_password is None:
        user_data.router_password = update.message.text.strip()
        message = "Semua informasi telah disimpan. Ketik /test untuk melanjutkan."
        update.message.reply_text(message)
    else:
        message = "Semua informasi telah disimpan. Ketik /test untuk melanjutkan."
        update.message.reply_text(message)

def info_command_handler(update, context):
    username_telegram = update.effective_user.username #username pengguna telegram
    message = f"Selamat datang, {username_telegram} ini adalah BOT Skytama\n\n" \
              "Bot ini hanya digunakan untuk staff / rekan SkyTaMa\n" \
              "Silahkan tekan /info untuk informasi lebih lanjut\n"
    update.message.reply_text(message)

def infolengkap_command_handler(update, context):
    message = "Berikut adalah command server *SkyTaMa*\n\n" \
            "/home Server Rumah\n" \
            "/feriz Server Feriz\n" \
            "/ngembat Server Ngembat\n" \
            "/iza Server Iza\n\n" \
            "Jika muncul pesan kendala (error) silahkan /exit terlebih dahulu\n\n" \
            "bot skytama versi 1.3"
    update.message.reply_text(message)

def send_message(bot, chat_id, message):
    bot.send_message(chat_id=chat_id, text=message, parse_mode='markdown')

def exit_command_handler(update, context):
    user_id = update.effective_user.id
    user_data = user_data_dict.get(user_id)

    if user_data:
        user_data.ip_address = None
        user_data.router_username = None
        user_data.router_password = None

    message = "Data telah di reset, lakukan command kembali atau buka /info untuk" \
    "informasi lebih lengkapnya"
    update.message.reply_text(message)

def main():
    # Inisialisasi bot Telegram
    updater = Updater(bot=bot)

    # Menambahkan handler untuk command /<perintah>
    updater.dispatcher.add_handler(CommandHandler('test', start_command_handler))
    updater.dispatcher.add_handler(CommandHandler('start', info_command_handler))
    updater.dispatcher.add_handler(CommandHandler('home', home_command_handler))
    updater.dispatcher.add_handler(CommandHandler('feriz', feriz_command_handler))
    updater.dispatcher.add_handler(CommandHandler('ngembat', ngembat_command_handler))
    updater.dispatcher.add_handler(CommandHandler('iza', iza_command_handler))
    updater.dispatcher.add_handler(CommandHandler('exit', exit_command_handler))
    updater.dispatcher.add_handler(CommandHandler('info', infolengkap_command_handler))
    updater.dispatcher.add_handler(CommandHandler('custom', custom_command_handler))

    # Menambahkan handler untuk menerima input IP, username, dan password
    updater.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_input))

    # Memulai polling pesan dari Telegram
    updater.start_polling()

    # Menjaga agar program tetap berjalan
    updater.idle()

def custom_command_handler(update, context):
    user_id = update.effective_user.id
    user_data = user_data_dict.get(user_id)

    if user_data:
        user_data.ip_address = None
        user_data.router_username = None
        user_data.router_password = None

    start_command_handler(update, context)

def home_command_handler(update, context):
    server_data = os.environ.get('SERVER_HOME').split(',')
    user_id = update.effective_user.id
    user_data = user_data_dict.get(user_id)

    if user_data is None:
        user_data = UserData()
        user_data_dict[user_id] = user_data

    user_data.ip_address = server_data[0]
    user_data.router_username = server_data[1]
    user_data.router_password = server_data[2]
    message = "Lanjutkan /test untuk menjalankan program"
    update.message.reply_text(message)

def feriz_command_handler(update, context):
    server_data = os.environ.get('SERVER_FERIZ').split(',')
    user_id = update.effective_user.id
    user_data = user_data_dict.get(user_id)

    if user_data is None:
        user_data = UserData()
        user_data_dict[user_id] = user_data

    user_data.ip_address = server_data[0]
    user_data.router_username = server_data[1]
    user_data.router_password = server_data[2]
    message = "Lanjutkan /test untuk menjalankan program"
    update.message.reply_text(message)

def ngembat_command_handler(update, context):
    server_data = os.environ.get('SERVER_NGEMBAT').split(',')
    user_id = update.effective_user.id
    user_data = user_data_dict.get(user_id)

    if user_data is None:
        user_data = UserData()
        user_data_dict[user_id] = user_data

    user_data.ip_address = server_data[0]
    user_data.router_username = server_data[1]
    user_data.router_password = server_data[2]
    message = "Lanjutkan /test untuk menjalankan program"
    update.message.reply_text(message)

def iza_command_handler(update, context):
    server_data = os.environ.get('SERVER_IZA').split(',')
    user_id = update.effective_user.id
    user_data = user_data_dict.get(user_id)

    if user_data is None:
        user_data = UserData()
        user_data_dict[user_id] = user_data

    user_data.ip_address = server_data[0]
    user_data.router_username = server_data[1]
    user_data.router_password = server_data[2]
    message = "Lanjutkan /test untuk menjalankan program"
    update.message.reply_text(message)
    

if __name__ == '__main__':
    main()
