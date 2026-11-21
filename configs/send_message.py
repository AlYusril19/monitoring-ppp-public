from telegram import Bot
from dotenv import load_dotenv

import requests
from io import BytesIO
from configs.navigation import home_keyboard

import os

load_dotenv()

# Send Message to Users
telegram_bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
bot = Bot(token=telegram_bot_token)

# Send Message to Admin
chat_admin_ids = os.environ.get('ALLOWED_ADMIN_IDS')
allowed_admin_ids = set(map(int, chat_admin_ids.split(',')))

# Log Activity (Send Message to Admin)
telegram_bot_log_token = os.environ.get('TELEGRAM_BOT_LOG_TOKEN')
chat_log = int(os.environ.get('LOG_USER_ID'))
bot_log = Bot(token=telegram_bot_log_token)

# Send Message Text
def send_message(bot, chat_id, message, with_dashboard=True):
    """Send a response with a Dashboard shortcut unless explicitly disabled."""
    reply_markup = home_keyboard() if with_dashboard else None
    return bot.send_message(chat_id=chat_id, text=message, parse_mode='markdown', reply_markup=reply_markup)

# Send Message Image
def send_image(bot, chat_id, image_url):
    try:
        # Mengambil gambar dari URL
        response = requests.get(image_url)
        image_bytes = BytesIO(response.content)

        # Mengirim gambar ke grup atau pengguna
        bot.send_photo(chat_id=chat_id, photo=image_bytes)
    except Exception as e:
        print("Error saat mengirim gambar:", str(e))
