from models.userdata import UserData, user_data_dict
from handlers.handler_onboarding import handle_onboarding_input
from handlers.handler_server import handle_server_wizard
from handlers.handler_start import handle_custom_server_input

def handle_input(update, context):
    if (handle_onboarding_input(update, context)
            or handle_server_wizard(update, context)
            or handle_custom_server_input(update, context)):
        return
    user_id = update.effective_user.id
    user_data = user_data_dict.get(user_id)
    text_message = "Semua informasi telah disimpan.\n"\
                    "Ketik /testppp untuk monitoring jaringan.\n"\
                    "Ketik /traffic untuk monitoring traffic interface"
    if user_data is None:
        user_data = UserData()
        user_data_dict[user_id] = user_data

    # Mendapatkan input dari pengguna
    if user_data.ip_address is None:
        user_data.ip_address = update.message.text.strip()
        message = "Silakan masukkan username:"
        update.message.reply_text(message)

    elif user_data.router_username is None:
        user_data.router_username = update.message.text.strip()
        message = "Silakan masukkan password:"
        update.message.reply_text(message)

    elif user_data.router_password is None:
        user_data.router_password = update.message.text.strip()
        update.message.reply_text(text_message)
        return

    elif user_data.interface is None:
        user_data.interface = update.message.text.strip()
        message = "Semua informasi telah disimpan. Ketik /traffic untuk melanjutkan."
        update.message.reply_text(message)
        return
    else:
        update.message.reply_text(text_message)
