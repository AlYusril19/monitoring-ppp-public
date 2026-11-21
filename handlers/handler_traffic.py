from librouteros import connect
import requests
from io import BytesIO
from configs.send_message import send_message, send_image, chat_log, bot_log, allowed_admin_ids
from models.userdata import UserData, user_data_dict
from handlers.handler_exit_interface import exit_interface_command_handler
from configs.data_json_user import load_user_data, save_user_data, get_registered_username
from configs.format_rupiah import format_rupiah
from configs.billing import charge_user
from configs.navigation import home_keyboard

def monitoring_command_handler(update, context):
    user_id = update.effective_user.id
    user_data = user_data_dict.get(user_id)
    saldo_user = load_user_data()

    if str(user_id) not in saldo_user and user_id not in allowed_admin_ids:
        update.message.reply_text("Anda belum terdaftar lakukan /daftar terlebih dahulu.")
        return
    
    if user_data is None:
        update.message.reply_text("Server tidak ditemukan.")
        return
    
    if user_data.interface is None:
        update.effective_message.reply_text('Pilih interface dari menu Traffic terlebih dahulu.')
        return
    
    else:
        run_traffic_monitoring(context, user_id, update.effective_chat.id, user_data)

def run_traffic_monitoring(context, user_id, chat_id, user_data):
    username_telegram = get_registered_username(user_id)
    bot = context.bot
    send_message(bot, chat_id, "Waiting in Process")
    success, start_cost, remaining = charge_user(user_id, "traffic")
    if not success:
        send_message(bot, chat_id, "Mohon maaf saldo anda tidak mencukupi, silahkan melakukan topup saldo")
        return
    
    # Mendapatkan URL gambar berdasarkan interface yang dipilih
    image_url = f'http://{user_data.ip_address}/graphs/iface/{user_data.interface}/daily.gif'
    send_message(bot, chat_id, f"{user_data.interface}")

    # Mengirim gambar ke grup atau pengguna
    send_image(bot, chat_id, image_url)
    # send_message(bot,chat_id,"ketik interface untuk mengecek traffic kembali contoh : (ether1)")
    # pesan log ke admin
    send_message(bot_log, chat_log,f"user *{username_telegram or user_id}* Monitoring LB {user_data.interface} \n")  
    send_message(bot,chat_id, f"biaya transaksi sebesar Rp{start_cost}")
    # pesan log ke admin
    saldo_format = format_rupiah(remaining or 0)
    send_message(bot_log, chat_log,f"user *{username_telegram or user_id}* Monitoring LB {user_data.interface} \n" \
                                    f"Sisa saldo User {saldo_format}")
    user_data.interface = None
    bot.send_message(chat_id=chat_id, text="Pilih aksi berikutnya:", reply_markup=home_keyboard())


# Compatibility for callers from older conversation code.
def monitoring_command_handler_after_input(update, context, user_data, username_telegram, saldo_user, user_id):
    return run_traffic_monitoring(context, user_id, update.effective_chat.id, user_data)
