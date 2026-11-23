from configs.data_json_user import load_user_data
from configs.format_rupiah import format_rupiah
from configs.navigation import home_keyboard, topup_keyboard
from configs.send_message import send_message

def cek_saldo(update, context):
    """/saldo: saldo user + tombol Isi Saldo."""
    bot = context.bot
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user_data = load_user_data()
    if str(user_id) in user_data:
        saldo = user_data[str(user_id)]['saldo']
        saldo_format = format_rupiah(saldo)  # Format saldo menjadi IDR
        message = "```Saldo "\
                    f"Saldo Anda: {saldo_format}\n"\
                    "Untuk cek total transaksi gunakan command:```\n"\
                    "/historybulanan\n"\
                    "/historytahunan"
        send_message(bot, chat_id, message, reply_markup=topup_keyboard())
    else:
        context.bot.send_message(chat_id=user_id, text="Anda belum terdaftar.", reply_markup=home_keyboard())