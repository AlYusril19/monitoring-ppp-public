from models.userdata import user_data_dict

def exit_command_handler(update, context):
    user_id = update.effective_user.id
    user_data = user_data_dict.get(user_id)

    if user_data:
        user_data.ip_address = None
        user_data.router_username = None
        user_data.router_password = None
        user_data.interface = None

    message = "Data telah di reset"
    update.message.reply_text(message)