from models.userdata import user_data_dict

def exit_interface_command_handler(update, context):
    user_id = update.effective_user.id
    user_data = user_data_dict.get(user_id)

    if user_data:
        user_data.interface = None

    # message = "data interface telah dihapus"
    # update.message.reply_text(message)