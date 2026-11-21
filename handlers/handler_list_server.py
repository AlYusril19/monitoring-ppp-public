from configs.data_json_user import load_user_data

def list_servers(update, context):
    user_id = update.effective_user.id
    user_data = load_user_data()

    if str(user_id) in user_data and "servers" in user_data[str(user_id)]:
        servers = user_data[str(user_id)]["servers"]
        if servers:
            message = "Daftar server Anda:\n\n"
            for server in servers:
                message += f"Nama: {server['name']}, IP: {server['ip']}\n"
            update.message.reply_text(message)
            update.message.reply_text("gunakan /connect untuk menghubungkan ke server")
        else:
            update.message.reply_text("Anda belum menambahkan server.")
    else:
        update.message.reply_text("Anda belum terdaftar atau belum menambahkan server.")