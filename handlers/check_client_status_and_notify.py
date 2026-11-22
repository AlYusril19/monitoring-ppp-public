from librouteros import connect
from configs.send_message import send_message, chat_log, bot_log, allowed_admin_ids
from configs.mikrotik_function import get_down_users
from configs.data_json_user import load_user_data, save_user_data, get_last_notification_time, save_last_notification_time
from configs.format_rupiah import format_rupiah
from configs.app_settings import get_monitoring_config, get_price, is_staff
from configs.billing import charge_user
from datetime import datetime, timedelta
from configs.add_transaction import add_transaction
import time
import pytz

TIMEZONE = pytz.timezone('Asia/Jakarta')

def check_client_status_and_notify(context):
    bot = context.bot
    user_data = load_user_data()
    now = datetime.now(TIMEZONE)

    for user_id, data in user_data.items():
        user_id = int(user_id)
        username_telegram = data.get("username_telegram", str(user_id))
        config = get_monitoring_config(data)
        state = data.setdefault("monitoring_state", {})
        if state.get("paused"):
            continue
        interval = int(config["alert_interval_minutes"] if state.get("alert_active")
                       else config["normal_interval_minutes"])
        last_check = state.get("last_check_at")
        if last_check:
            try:
                last_check_at = TIMEZONE.localize(datetime.strptime(last_check, '%Y-%m-%d %H:%M:%S'))
                if now - last_check_at < timedelta(minutes=interval):
                    continue
            except ValueError:
                pass
        state["last_check_at"] = now.strftime('%Y-%m-%d %H:%M:%S')
        save_user_data(user_data)

        for server in data["servers"]:
            try:
                # Membuat koneksi ke MikroTik
                connection = connect(
                    username=server["username"],
                    password=server["password"],
                    host=server["ip"]
                )

                nama_server = server["name"]
                server_state = state.setdefault("servers", {}).setdefault(nama_server, {})

                # Cek apakah login berhasil
                if connection:
                    
                    # Mendapatkan semua pengguna yang statusnya "down"
                    down_users = get_down_users(connection, config.get("excluded_profiles"))
                    if len(down_users) >= int(config["notify_down_threshold"]):
                        down_users_message = f"Client PPPOE status *DOWN ({len(down_users)} users)*:\n\n"
                        for username, last_logged_out in down_users:
                            down_users_message += f"❌ {username} - ({last_logged_out})\n"

                        # Pesan Warning Down PPP
                        warning_message = ""
                        if len(down_users) >= int(config["warning_threshold"]):
                            warning_message = f"*Warning* ⚠️ Harap segera dicek lebih lanjut! /why?"
                        if len(down_users) >= int(config["critical_threshold"]):
                            warning_message = f"*Warning* 🚨 Harap segera dicek lebih lanjut! /why?"

                        # Only the first DOWN state is charged/notified.  Subsequent
                        # checks use the longer alert interval until recovery.
                        if not server_state.get("alert_active"):
                            success, start_cost, remaining = charge_user(user_id, "notify")
                            if not success:
                                send_message(bot, user_id, "Saldo tidak cukup untuk notifikasi monitoring. Monitoring dihentikan sementara.")
                                state["paused"] = True
                                server_state["paused"] = True
                                save_user_data(user_data)
                                continue
                            send_message(bot, user_id, down_users_message)
                            if warning_message:
                                send_message(bot, user_id, warning_message)
                            send_message(bot, user_id, "\n*Notifikasi otomatis.* Cek berikutnya memakai interval alert yang lebih panjang.\n" \
                                                    f"Biaya notifikasi: Rp{start_cost}")
                            server_state["alert_active"] = True
                            server_state["last_alert_at"] = now.strftime('%Y-%m-%d %H:%M:%S')
                            state["alert_active"] = True
                            save_user_data(user_data)

                            # pesan log ke admin
                            saldo_format = format_rupiah(load_user_data().get(str(user_id), {}).get("saldo", 0))
                            send_message(bot_log, chat_log, f"user *{username_telegram}* login Otomatis ke *{nama_server}*\n" \
                                                            f"User Down *({len(down_users)} Users*)\n" \
                                                            f"{warning_message}\n"\
                                                            f"Sisa saldo User {saldo_format}")

                            save_last_notification_time(user_id, now.strftime('%Y-%m-%d %H:%M:%S'))
                    else:
                        if server_state.get("alert_active"):
                            send_message(bot, user_id, f"✅ Status PPPoE di *{nama_server}* sudah pulih. Monitoring kembali ke interval normal.")
                        server_state["alert_active"] = False
                        state["alert_active"] = any(
                            item.get("alert_active") for item in state.get("servers", {}).values())
                        save_user_data(user_data)
                else:
                    send_message(bot, user_id, "Notifikasi otomatis error, periksa data server anda")
            except Exception as e:
                print("Terjadi kesalahan:", str(e))
                send_message(bot, user_id, f"Terjadi kesalahan: {str(e)}")
