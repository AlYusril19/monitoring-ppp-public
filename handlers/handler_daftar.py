from configs.send_message import allowed_admin_ids
from configs.data_json_user import load_user_data, save_user_data, get_registered_username
from configs.send_message import bot_log, send_message, chat_log
from configs.add_transaction import add_transaction
from configs.get_current_time import get_current_time

def daftar(update, context):
    # Mengecek apakah pengguna adalah admin yang diizinkan
    user_id = update.effective_user.id
    if user_id in allowed_admin_ids:
        daftar_for_admin(update, context)
    else:
        daftar_for_client(update, context)

def daftar_for_admin(update, context):
    args = context.args
    if len(args) == 3:
        user_id = int(args[0])
        username_telegram = str(args[1])
        nohp = int(args[2])
        user_data = load_user_data()
        saldo_awal = 5000

        if str(user_id) in user_data:
            context.bot.send_message(chat_id=update.effective_chat.id, text=f"Client {username_telegram} sudah terdaftar")
            return
        else:
            user_data[str(user_id)] = {
                "user_id": user_id,
                "username_telegram": username_telegram,
                "nohp": nohp,
                "saldo": saldo_awal,
                "created_at": get_current_time(),
                "servers": [],
                "aktif": True,  # ✅ langsung aktif kalau didaftarkan oleh admin
                "account_type": "client",
            }

        save_user_data(user_data)
        add_transaction(user_id, saldo_awal, "saldo_awal")

        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Pelanggan {username_telegram} telah sukses didaftarkan dan langsung aktif.\nGunakan /topup untuk menambah saldo."
        )
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Format yang benar: /daftar <user_id> <username_telegram> <nohp>"
        )

def daftar_for_client(update, context):
    user_id = update.effective_user.id
    user_data = load_user_data()
    saldo_awal = 5000

    if str(user_id) in user_data:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Anda sudah terdaftar")
        return

    args = context.args
    if len(args) == 1:
        nohp = int(args[0])
        username_telegram = update.effective_user.username  # username pengguna telegram

        user_data[str(user_id)] = {
            "user_id": user_id,
            "nohp": nohp,
            "username_telegram": username_telegram,
            "saldo": saldo_awal,
            "created_at": get_current_time(),
            "servers": [],
            "aktif": False,  # 🚨 tambahkan ini agar status default arsip
            "account_type": "client",
        }

        save_user_data(user_data)
        add_transaction(user_id, saldo_awal, "saldo_awal")

        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                f"Selamat bergabung {username_telegram}\n"
                "Hubungi admin untuk mengaktifkan akun Anda.\n"
                "Gunakan /info untuk informasi lengkap.\n"
                f"Anda mendapatkan bonus saldo kredit {saldo_awal}"
            )
        )

        registered_name = get_registered_username(user_id)
        send_message(bot_log, chat_log, f"📥 Pendaftar baru username: *{registered_name}* - {user_id}")
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "Format yang benar: /daftar <nomor_hp>\n"
                "Jika username Telegram belum di-set, silakan set terlebih dahulu."
            )
        )
