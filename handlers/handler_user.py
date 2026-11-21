from configs.data_json_user import load_user_data, save_user_data
from configs.send_message import allowed_admin_ids, send_message
from configs.format_rupiah import format_rupiah

def arsipkan_user(update, context):
    bot = context.bot
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if user_id in allowed_admin_ids:
        args = context.args
        if not args:
            send_message(bot, chat_id, "Gunakan: /arsipkan_user <user_id>")
            return

        target_id = args[0]
        user_data = load_user_data()

        if target_id in user_data:
            user_data[target_id]['aktif'] = False
            save_user_data(user_data)
            send_message(bot, chat_id, f"✅ User `{target_id}` berhasil diarsipkan.")
        else:
            send_message(bot, chat_id, f"❌ User `{target_id}` tidak ditemukan.")
    else:
        send_message(bot, chat_id, "❌ Akses ditolak.")

def aktifkan_user(update, context):
    bot = context.bot
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if user_id in allowed_admin_ids:
        args = context.args
        if not args:
            send_message(bot, chat_id, "Gunakan: /aktifkan_user <user_id>")
            return

        target_id = args[0]
        user_data = load_user_data()

        if target_id in user_data:
            user_data[target_id]['aktif'] = True
            save_user_data(user_data)
            send_message(bot, chat_id, f"✅ User `{target_id}` telah diaktifkan kembali.")
        else:
            send_message(bot, chat_id, f"❌ User `{target_id}` tidak ditemukan.")
    else:
        send_message(bot, chat_id, "❌ Akses ditolak.")

def user_aktif(update, context):
    bot = context.bot
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if user_id in allowed_admin_ids:
        user_data = load_user_data()
        aktif_users = []

        for uid, info in user_data.items():
            if info.get('aktif', True):  # Default dianggap aktif
                username = info.get('username_telegram', 'Tidak diketahui')
                saldo = format_rupiah(info.get('saldo', 0))
                aktif_users.append(f"👤 `{uid}` - {username} - {saldo}")

        if aktif_users:
            message = "📋 *Daftar User Aktif:*\n\n" + "\n".join(aktif_users)
        else:
            message = "Tidak ada user yang aktif."

        send_message(bot, chat_id, message)
    else:
        send_message(bot, chat_id, "❌ Akses ditolak.")

def user_arsip(update, context):
    bot = context.bot
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if user_id in allowed_admin_ids:
        user_data = load_user_data()
        if not user_data:
            send_message(bot, chat_id, "Belum ada data pengguna.")
            return

        arsip_message = "📦 *Daftar User Arsip:*\n\n"
        ada_arsip = False

        for uid, data in user_data.items():
            if not data.get("aktif", False):  # hanya ambil user yang tidak aktif
                ada_arsip = True
                username = data.get("username_telegram", "Tidak diketahui")
                nohp = data.get("nohp", "-")
                saldo_format = format_rupiah(data.get('saldo', 0))
                arsip_message += f"🆔 `{uid}` - @{username}\n📱 {nohp}\n {saldo_format}\n\n"

        if ada_arsip:
            send_message(bot, chat_id, arsip_message)
        else:
            send_message(bot, chat_id, "Tidak ada user dalam arsip.")
    else:
        send_message(bot, chat_id, "Akses ditolak.")
