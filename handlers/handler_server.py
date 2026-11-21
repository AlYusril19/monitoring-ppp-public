from configs.data_json_user import save_user_data, load_user_data
from configs.get_current_time import get_current_time

date_now = get_current_time


def start_server_wizard(query, context):
    """Start a sequential server form from an inline button."""
    context.user_data["server_wizard"] = {"step": "name"}
    query.answer()
    query.edit_message_text("Nama server apa yang ingin disimpan? Ketik /cancel untuk membatalkan.")


def handle_server_wizard(update, context):
    """Consume form input. Password messages are removed immediately."""
    wizard = context.user_data.get("server_wizard")
    if not wizard:
        return False
    value = update.effective_message.text.strip()
    step = wizard["step"]
    prompts = {
        "name": ("name", "Masukkan IP atau hostname MikroTik:"),
        "ip": ("ip", "Masukkan username RouterOS (gunakan akun READ):"),
        "username": ("username", "Masukkan password RouterOS. Pesan ini akan dihapus setelah dibaca:"),
    }
    if step in prompts:
        field, prompt = prompts[step]
        wizard[field] = value
        wizard["step"] = {"name": "ip", "ip": "username", "username": "password"}[step]
        update.effective_message.reply_text(prompt)
        return True

    if step == "password":
        wizard["password"] = value
        try:
            update.effective_message.delete()
        except Exception:
            pass
        users = load_user_data()
        record = users.get(str(update.effective_user.id))
        if not record:
            context.user_data.pop("server_wizard", None)
            update.effective_chat.send_message("Akun tidak ditemukan. Silakan registrasi kembali.")
            return True
        record.setdefault("servers", []).append({
            "name": wizard["name"], "ip": wizard["ip"], "username": wizard["username"],
            "password": wizard["password"], "created_at": get_current_time(), "updated_at": get_current_time(),
        })
        save_user_data(users)
        context.user_data.pop("server_wizard", None)
        update.effective_chat.send_message(
            f"✅ Server {wizard['name']} tersimpan. Password Anda sudah dihapus dari chat.")
        return True
    return False

def add_server(update, context):
    user_id = update.effective_user.id
    user_data = load_user_data()
    
    if str(user_id) in user_data:
        args = context.args
        if len(args) == 4:
            server_name = args[0]
            ip_address = args[1]
            username = args[2]
            password = args[3]

            # Inisialisasi server list jika belum ada
            if "servers" not in user_data[str(user_id)]:
                user_data[str(user_id)]["servers"] = []

            from datetime import datetime
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            user_data[str(user_id)]["servers"].append({
                "name": server_name,
                "ip": ip_address,
                "username": username,
                "password": password,
                "created_at": now,
                "updated_at": now
            })

            save_user_data(user_data)
            update.message.reply_text(f"Server {server_name} berhasil ditambahkan. Gunakan /listserver untuk melihat.")
        else:
            update.message.reply_text("Format yang benar: /addserver <nama_server> <ip_address> <username> <password>")
    else:
        update.message.reply_text("Anda tidak diizinkan menggunakan bot ini.")

def delete_server(update, context):
    user_id = update.effective_user.id
    user_data = load_user_data()
    
    if str(user_id) in user_data:
        args = context.args
        if len(args) == 1:
            server_name = args[0].strip().lower()

            if "servers" in user_data[str(user_id)] and user_data[str(user_id)]["servers"]:
                servers = user_data[str(user_id)]["servers"]
                updated_servers = [
                    server for server in servers 
                    if server["name"].strip().lower() != server_name
                ]

                if len(updated_servers) == len(servers):
                    update.message.reply_text(f"⚠️ Server *{server_name}* tidak ditemukan.")
                else:
                    user_data[str(user_id)]["servers"] = updated_servers
                    save_user_data(user_data)
                    update.message.reply_text(f"✅ Server *{server_name}* berhasil dihapus.")
            else:
                update.message.reply_text("⚠️ Anda belum menambahkan server apapun.")
        else:
            update.message.reply_text("📌 Format yang benar: /delserver <nama_server>")
    else:
        update.message.reply_text("🚫 Anda tidak diizinkan menggunakan bot ini.")

def edit_server(update, context):
    user_id = update.effective_user.id
    user_data = load_user_data()

    if str(user_id) in user_data:
        args = context.args
        if len(args) == 5:
            old_server_name = args[0].strip().lower()
            new_server_name = args[1]
            new_ip_address = args[2]
            new_username = args[3]
            new_password = args[4]

            servers = user_data[str(user_id)].get("servers", [])

            for server in servers:
                if server["name"].strip().lower() == old_server_name:
                    server["name"] = new_server_name
                    server["ip"] = new_ip_address
                    server["username"] = new_username
                    server["password"] = new_password
                    server["updated_at"] = get_current_time()

                    save_user_data(user_data)
                    update.message.reply_text(
                        f"✅ Server *{old_server_name}* berhasil diubah menjadi *{new_server_name}*."
                    )
                    return

            update.message.reply_text(f"⚠️ Server dengan nama *{old_server_name}* tidak ditemukan.")
        else:
            update.message.reply_text(
                "📌 Format yang benar:\n"
                "/editserver <nama_server_lama> <nama_server_baru> <ip_address_baru> <username_baru> <password_baru>"
            )
    else:
        update.message.reply_text("🚫 Anda tidak diizinkan menggunakan bot ini.")
