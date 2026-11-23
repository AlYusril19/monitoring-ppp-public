from telegram import ReplyKeyboardRemove

from configs.app_settings import staff_ids
from configs.chat_tracker import track_message
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
    """Saat bot start: perbarui versi di app_info.json dan kabari user aktif."""
    bot = context.bot
    user_data = load_user_data()
    current_info = {
        'app_version': APP_VERSION,
        'app_name': APP_NAME
    }
    app_info = load_app_info()
    last_version = app_info.get('app_version')

    # Step 1: Jika file belum ada, buat dengan nilai dari .env
    # Selalu update di atas data lama agar settings dan antrian
    # registrasi/topup di app_info.json tidak ikut terhapus.
    if not app_info:
        app_info.update(current_info)
        save_app_info(app_info)
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
            # Update informasi di file (hanya versi & nama, data lain dipertahankan)
            app_info.update(current_info)
            save_app_info(app_info)
        else:
            message = (
                "*Informasi:* Bot telah direboot.\n"
                "Silahkan cek data anda, terimakasih."
            )

    # Tutup bar "Reply to ..." peninggalan form lama, sebelum pesan startup.
    active_ids = {int(uid) for uid, data in user_data.items()
                  if not isinstance(data, dict) or data.get('aktif', True)}
    clear_reply_interface(bot, active_ids | staff_ids())

    # Kirim pesan ke semua pengguna beserta home_keyboard()
    for user_id, data in user_data.items():
        if isinstance(data, dict) and not data.get('aktif', True):
            continue  # user arsip tidak dikirimi pesan
        try:
            sent = bot.send_message(
                chat_id=int(user_id),
                text=message,
                parse_mode='Markdown',
                reply_markup=home_keyboard()
            )
            track_message(sent)  # removed at the user's next action
        except Exception as e:
            # User yang memblokir bot tidak boleh menghentikan startup.
            print(f"Gagal kirim pesan startup ke {user_id}: {e}")


def clear_reply_interface(bot, chat_ids):
    """One-time cleanup of the "Reply to <bot>" bar left by old ForceReply prompts.

    Telegram clients keep a ForceReply state until a newer message removes it.
    A silent message with ReplyKeyboardRemove clears that state; it is deleted
    right away so the chat stays clean. Each chat is cleaned once (stored in
    app_info.json → reply_ui_cleared), so later restarts send nothing.
    """
    app_info = load_app_info()
    done = {int(cid) for cid in app_info.get('reply_ui_cleared', [])}
    pending = sorted(set(chat_ids) - done)
    if not pending:
        return
    for chat_id in pending:
        try:
            message = bot.send_message(chat_id=chat_id, text="🔄", reply_markup=ReplyKeyboardRemove(),
                                       disable_notification=True)
        except Exception as e:
            # Not started/blocked chats are retried at the next restart.
            print(f"Gagal membersihkan tampilan reply untuk {chat_id}: {e}")
            continue
        try:
            bot.delete_message(chat_id=chat_id, message_id=message.message_id)
        except Exception:
            pass
        done.add(chat_id)
    app_info = load_app_info()
    app_info['reply_ui_cleared'] = sorted(done)
    save_app_info(app_info)
