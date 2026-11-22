from configs.send_message import allowed_admin_ids
from configs.data_json_user import load_user_data, save_user_data, get_registered_username
from configs.send_message import bot_log, send_message, chat_log
from configs.add_transaction import add_transaction
from configs.get_current_time import get_current_time
from configs.app_settings import get_trial_balance

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
        saldo_awal = get_trial_balance()

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
        # Direct admin registration grants a trial credit, not operating revenue.
        if saldo_awal:
            add_transaction(user_id, saldo_awal, "trial_balance", {"trial_balance": saldo_awal})

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
    # Prevent the legacy command from bypassing the admin approval queue.
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Registrasi sekarang melalui /start agar masuk antrian persetujuan admin.")
