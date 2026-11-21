from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from configs.app_settings import get_monitoring_config
from configs.data_json_user import load_user_data, save_user_data


def _keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Normal 10m", callback_data="mon:n:10"),
         InlineKeyboardButton("Normal 20m", callback_data="mon:n:20"),
         InlineKeyboardButton("Normal 30m", callback_data="mon:n:30")],
        [InlineKeyboardButton("Alert 60m", callback_data="mon:a:60"),
         InlineKeyboardButton("Alert 120m", callback_data="mon:a:120"),
         InlineKeyboardButton("Alert 240m", callback_data="mon:a:240")],
        [InlineKeyboardButton("▶ Lanjutkan", callback_data="mon:resume"),
         InlineKeyboardButton("⏸ Jeda", callback_data="mon:pause")],
        [InlineKeyboardButton("🏠 Dashboard", callback_data="nav:home")],
    ])


def monitoring_settings(update, context):
    user_id = str(update.effective_user.id)
    users = load_user_data()
    if user_id not in users:
        update.effective_message.reply_text("Anda belum terdaftar.")
        return
    config = get_monitoring_config(users[user_id])
    state = users[user_id].get("monitoring_state", {})
    status = "dijeda" if state.get("paused") else "aktif"
    update.effective_message.reply_text(
        "⚙️ *Pengaturan Monitoring*\n"
        f"Interval normal: *{config['normal_interval_minutes']} menit*\n"
        f"Setelah alert/down: *{config['alert_interval_minutes']} menit*\n"
        f"Status: *{status}*",
        parse_mode="Markdown", reply_markup=_keyboard())


def monitoring_callback(query):
    parts = query.data.split(":")
    users = load_user_data()
    record = users.get(str(query.from_user.id))
    if not record:
        query.answer("Anda belum terdaftar.", show_alert=True)
        return
    if len(parts) == 3:
        value = int(parts[2])
        record.setdefault("monitoring", {})[
            "normal_interval_minutes" if parts[1] == "n" else "alert_interval_minutes"
        ] = value
        message = "Interval disimpan."
    else:
        record.setdefault("monitoring_state", {})["paused"] = parts[1] == "pause"
        message = "Monitoring dijeda." if parts[1] == "pause" else "Monitoring dilanjutkan."
    save_user_data(users)
    query.answer(message)
    config = get_monitoring_config(record)
    status = "dijeda" if record.get("monitoring_state", {}).get("paused") else "aktif"
    query.edit_message_text(
        "⚙️ *Pengaturan Monitoring*\n"
        f"Interval normal: *{config['normal_interval_minutes']} menit*\n"
        f"Setelah alert/down: *{config['alert_interval_minutes']} menit*\n"
        f"Status: *{status}*",
        parse_mode="Markdown", reply_markup=_keyboard())
