from librouteros import connect
from configs.send_message import send_message, chat_log, bot_log, allowed_admin_ids
from configs.mikrotik_function import get_name_server, get_down_users
from models.userdata import UserData, user_data_dict
from handlers.handler_exit import exit_command_handler
from configs.data_json_user import load_user_data, save_user_data, get_registered_username
from configs.format_rupiah import format_rupiah
from configs.billing import charge_user
from configs.app_settings import get_monitoring_config, get_price
from configs.navigation import home_keyboard, session_action_keyboard, wizard_keyboard

def start_command_handler(update, context):
    user_id = update.effective_user.id
    saldo_user = load_user_data()

    # Pengecekan Saldo
    if str(user_id) not in saldo_user and user_id not in allowed_admin_ids:
        update.effective_message.reply_text("Anda belum terdaftar, silahkan /start untuk registrasi.")
        return

    user_data = user_data_dict.get(user_id)

    if user_data is None:
        update.effective_message.reply_text("Anda belum terhubung ke server.\n"\
                                  "gunakan /connect atau /custom untuk menghubungkan ke server")
    else:
        # Jika semua data ada, lanjutkan dengan proses normal
        start_command_handler_after_input(update, context, user_data, saldo_user, user_id)
        
def start_command_handler_by_custom(update, context):
    return begin_custom_server(context, update.effective_user.id, update.effective_message)


def begin_custom_server(context, user_id, message):
    """Start a temporary server session; it is never written to datauser.json."""
    context.user_data["custom_server_wizard"] = {"step": "ip"}
    message.reply_text(
        "🔧 *Server Custom*\nMasukkan IP atau hostname MikroTik. Data ini hanya dipakai untuk sesi saat ini dan tidak disimpan.",
        parse_mode="Markdown", reply_markup=wizard_keyboard("custom"))


def handle_custom_server_input(update, context):
    """Consume temporary server credentials and delete the password message."""
    wizard = context.user_data.get("custom_server_wizard")
    if not wizard:
        return False
    value = update.effective_message.text.strip()
    step = wizard["step"]
    if step == "ip":
        wizard["ip"] = value
        wizard["step"] = "username"
        update.effective_message.reply_text("Masukkan username RouterOS (gunakan akun READ):", reply_markup=wizard_keyboard("custom"))
        return True
    if step == "username":
        wizard["username"] = value
        wizard["step"] = "password"
        update.effective_message.reply_text("Masukkan password. Pesan password akan dihapus setelah diterima:", reply_markup=wizard_keyboard("custom"))
        return True
    if step == "password":
        try:
            update.effective_message.delete()
        except Exception:
            pass
        session = user_data_dict.setdefault(update.effective_user.id, UserData())
        session.ip_address = wizard["ip"]
        session.router_username = wizard["username"]
        session.router_password = value
        session.interface = None
        context.user_data.pop("custom_server_wizard", None)
        update.effective_chat.send_message(
            "✅ Server custom tersambung untuk sesi ini. Password telah dihapus dari chat. Pilih aksi berikutnya:",
            reply_markup=session_action_keyboard())
        return True
    return False


def start_command_handler_after_input(update, context, user_data, saldo_user, user_id):
    return run_pppoe_test(context, user_id, update.effective_chat.id, user_data)


def run_pppoe_test(context, user_id, chat_id, user_data):
    """Run the PPPoE test from either a command or an inline callback."""
    # Logs must use the registration record, not a mutable Telegram username.
    username_telegram = get_registered_username(user_id)
    message = "Waiting in Process!!"
    bot = context.bot
    send_message(bot, chat_id, message)

    try:
        # Membuat koneksi ke MikroTik
        connection = connect(
            username=user_data.router_username,
            password=user_data.router_password,
            host=user_data.ip_address
        )

        nama_server = get_name_server(connection)

        # Cek apakah login berhasil
        if connection:
            success, start_cost, remaining = charge_user(user_id, "testppp")
            if not success:
                send_message(bot, chat_id, "Mohon maaf saldo anda tidak mencukupi, silahkan melakukan topup saldo")
                return
            
            # Kirim pesan user
            send_message(bot, chat_id, f"Login ke *{nama_server}*")

            # Mendapatkan semua pengguna yang statusnya "down"
            config = get_monitoring_config(load_user_data().get(str(user_id), {}))
            down_users = get_down_users(connection, config.get("excluded_profiles"))
            notify_threshold = int(config["notify_down_threshold"])
            if len(down_users) >= notify_threshold:
                down_users_message = f"Client PPPOE status *DOWN ({len(down_users)} users)*:\n\n"
                for username, last_logged_out in down_users:
                    down_users_message += f"❌ {username} - ({last_logged_out})\n"
                
                # Pesan Warning Down PPP
                warning_message = ""
                if len(down_users) >= int(config["warning_threshold"]):
                    warning_message = f"*Warning* ⚠️ Harap segera dicek lebih lanjut! /why?"
                if len(down_users) >= int(config["critical_threshold"]):
                    warning_message = f"*Warning* 🚨 Harap segera dicek lebih lanjut! /why?"
                
                # Pesan Down PPP ke User Telegram
                send_message(bot, chat_id, down_users_message)
                # Jika notif warning maka akan kirim pesan
                if warning_message:
                    send_message(bot, chat_id, warning_message)
                    
                send_message(bot, chat_id, f"biaya transaksi sebesar Rp{start_cost}")
                
                # pesan log ke admin
                saldo_format = format_rupiah(remaining or 0)
                send_message(bot_log, chat_log,f"user *{username_telegram}* login ke *{nama_server}*\n" \
                                              f"User Down *({len(down_users)} Users*)\n" \
                                              f"{warning_message}\n"\
                                              f"Sisa saldo User {saldo_format}")
            elif down_users:
                # A manual test still confirms the router was checked, but does not
                # turn a small outage into an alert when the user chose a higher limit.
                send_message(
                    bot, chat_id,
                    f"Terdeteksi {len(down_users)} pelanggan down, tetapi belum mencapai batas notifikasi Anda "
                    f"({notify_threshold} pelanggan). Tidak ada alert down yang ditampilkan.")
                send_message(bot, chat_id, f"biaya transaksi sebesar Rp{start_cost}")
                saldo_format = format_rupiah(remaining or 0)
                send_message(bot_log, chat_log, f"user *{username_telegram}* tes PPPoE ke *{nama_server}*\n" \
                                                f"Down di bawah batas notifikasi ({len(down_users)}/{notify_threshold})\n" \
                                                f"Sisa saldo User {saldo_format}")
            else:
                send_message(bot, chat_id, "User Status UP Semua 🤩")
                send_message(bot,chat_id, f"biaya transaksi sebesar Rp{start_cost}")
                # pesan log ke admin
                saldo_format = format_rupiah(remaining or 0)
                send_message(bot_log, chat_log,f"user *{username_telegram}* login ke *{nama_server}*\n" \
                                               f"Sisa saldo User {saldo_format}")
            bot.send_message(chat_id=chat_id, text="Pilih aksi berikutnya:", reply_markup=session_action_keyboard())
        else:
            send_message(bot, chat_id, "Login Gagal")
            bot.send_message(chat_id=chat_id, text="Kembali ke dashboard:", reply_markup=home_keyboard())
    except Exception as e:
        print("Terjadi kesalahan:", str(e))
        send_message(bot, chat_id, f"Terjadi kesalahan: {str(e)}")
        user_data.ip_address = None
        user_data.router_username = None
        user_data.router_password = None
        user_data.interface = None
        bot.send_message(chat_id=chat_id, text="Kembali ke dashboard:", reply_markup=home_keyboard())
