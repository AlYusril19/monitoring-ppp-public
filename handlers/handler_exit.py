from models.userdata import user_data_dict
from configs.navigation import home_keyboard

def exit_command_handler(update, context):
    user_id = update.effective_user.id
    user_data_dict.pop(user_id, None)
    update.effective_message.reply_text(
        "✅ Logout router berhasil. Koneksi server untuk sesi ini telah dibersihkan.",
        reply_markup=home_keyboard())
