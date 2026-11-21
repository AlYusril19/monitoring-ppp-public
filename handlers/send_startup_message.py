from configs.send_message import send_message
from configs.data_json_user import load_user_data, save_app_info, load_app_info
from configs.navigation import home_keyboard

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the APP_VERSION from environment variables, default to '1.0.0' if not set
APP_VERSION = os.environ.get('APP_VERSION', '1.0.0')
APP_NAME = os.environ.get('APP_NAME', 'MyBot')

def send_startup_message(context):
    bot = context.bot
    user_data = load_user_data()
    current_info = {
        'app_version': APP_VERSION,
        'app_name': APP_NAME
    }
    app_info = load_app_info()
    last_version = app_info.get('app_version')

    # Step 1: Jika file belum ada, buat dengan nilai dari .env
    if not app_info:
        save_app_info(current_info)
        message = (
            f"*Informasi:* Selamat Datang di {APP_NAME} {APP_VERSION}."
        )
    else:
        # Step 2 & 3: Jika file sudah ada, cek apakah versinya sama atau berbeda
        if APP_VERSION != last_version:
            message = (
                f"*Informasi:* Bot telah diperbarui ke versi {APP_VERSION}.\n"
                "Informasi update lebih lanjut /version."
            )
            # Update informasi di file
            save_app_info(current_info)
        else:
            message = (
                "*Informasi:* Bot telah direboot.\n"
                "Silahkan cek data anda, terimakasih."
            )

    # Kirim pesan ke semua pengguna beserta home_keyboard()
    for user_id, data in user_data.items():
        user_id = int(user_id)
        bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode='Markdown',
            reply_markup=home_keyboard()
        )
