from configs.data_json_user import load_user_data
from configs.send_message import allowed_admin_ids, send_message
from configs.format_rupiah import format_rupiah

def cek_semua_saldo(update, context):
    bot = context.bot
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    if user_id in allowed_admin_ids:
        user_data = load_user_data()
        if user_data:
            all_saldo_message = "💰 *Saldo semua user aktif:*\n\n"
            for uid, data in user_data.items():
                if isinstance(data, dict) and data.get('aktif', True):
                    saldo_format = format_rupiah(data.get('saldo', 0))
                    username_telegram = data.get('username_telegram', 'Nama Pengguna Tidak Tersedia')
                    all_saldo_message += f"👤 User `{uid}`, {username_telegram} \n"\
                                         f"    {saldo_format}\n"
            if all_saldo_message.strip() == "💰 *Saldo semua user aktif:*":
                all_saldo_message += "\n(Tidak ada user aktif)"
            send_message(bot, chat_id, all_saldo_message)
        else:
            send_message(bot, chat_id, "Tidak ada data user yang ditemukan.")
    else:
        send_message(bot, chat_id, "Akses ditolak.")
