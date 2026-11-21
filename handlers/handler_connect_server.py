from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters
from configs.data_json_user import load_user_data
from models.userdata import UserData, user_data_dict

SERVER_NAME = range(1)

def connect_to_server(update, context):
    update.message.reply_text("Masukkan nama server:")
    return SERVER_NAME

def server_name_handler(update, context):
    user_id = update.effective_user.id
    server_name = update.message.text
    user_data = load_user_data()

    if str(user_id) in user_data and "servers" in user_data[str(user_id)]:
        servers = user_data[str(user_id)]["servers"]
        server_data = next((server for server in servers if server["name"] == server_name), None)

        if server_data:
            ip_address = server_data["ip"]
            username = server_data["username"]
            password = server_data["password"]

            # Simpan data ke user_data_dict untuk keperluan selanjutnya
            if user_id not in user_data_dict:
                user_data_dict[user_id] = UserData()
            
            user_data_dict[user_id].ip_address = ip_address
            user_data_dict[user_id].router_username = username
            user_data_dict[user_id].router_password = password

            update.message.reply_text(f"Tersambung ke server {server_name}.\n"
                                      "Lanjutkan dengan /testppp untuk monitoring PPP.\n"
                                      "atau /traffic untuk monitoring traffic interface")
            return ConversationHandler.END
        else:
            update.message.reply_text("Server tidak ditemukan. Masukkan nama server yang benar:")
            return SERVER_NAME
    else:
        update.message.reply_text("Anda belum terdaftar atau belum menambahkan server.")
        return ConversationHandler.END
    
def cancel(update, context):
    update.message.reply_text('Operasi dibatalkan.')
    return ConversationHandler.END