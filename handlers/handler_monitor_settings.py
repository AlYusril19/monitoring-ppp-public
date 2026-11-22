from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from configs.app_settings import get_monitoring_config
from configs.data_json_user import load_user_data, save_user_data


def _keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Normal 10m", callback_data="mon:n:10"), InlineKeyboardButton("Normal 20m", callback_data="mon:n:20"), InlineKeyboardButton("Normal 30m", callback_data="mon:n:30")],
        [InlineKeyboardButton("Alert 60m", callback_data="mon:a:60"), InlineKeyboardButton("Alert 120m", callback_data="mon:a:120"), InlineKeyboardButton("Alert 240m", callback_data="mon:a:240")],
        [InlineKeyboardButton("🔔 Batas Notif", callback_data="mon:input:notify_down_threshold"), InlineKeyboardButton("⚠️ Warning", callback_data="mon:input:warning_threshold")],
        [InlineKeyboardButton("🚨 Warning Kritis", callback_data="mon:input:critical_threshold"), InlineKeyboardButton("👥 Profile Dikecualikan", callback_data="mon:profiles")],
        [InlineKeyboardButton("▶ Lanjutkan", callback_data="mon:resume"), InlineKeyboardButton("⏸ Jeda", callback_data="mon:pause")],
        [InlineKeyboardButton("🏠 Dashboard", callback_data="nav:home")],
    ])


def _summary(record):
    config = get_monitoring_config(record)
    status = "dijeda" if record.get("monitoring_state", {}).get("paused") else "aktif"
    profiles = ", ".join(config["excluded_profiles"]) or "tidak ada"
    return (
        "⚙️ *Pengaturan Monitoring*\n"
        f"Interval normal: *{config['normal_interval_minutes']} menit*\n"
        f"Setelah alert/down: *{config['alert_interval_minutes']} menit*\n"
        f"Kirim notif minimal: *{config['notify_down_threshold']} pelanggan down*\n"
        f"Warning ⚠️: *{config['warning_threshold']} pelanggan down*\n"
        f"Warning 🚨: *{config['critical_threshold']} pelanggan down*\n"
        f"Profile dikecualikan: `{profiles}`\nStatus: *{status}*")


def monitoring_settings(update, context):
    users = load_user_data()
    record = users.get(str(update.effective_user.id))
    if not record:
        update.effective_message.reply_text("Anda belum terdaftar.")
        return
    update.effective_message.reply_text(_summary(record), parse_mode="Markdown", reply_markup=_keyboard())


def monitoring_callback(query, context):
    parts = query.data.split(":")
    users = load_user_data()
    record = users.get(str(query.from_user.id))
    if not record:
        query.answer("Anda belum terdaftar.", show_alert=True)
        return
    if len(parts) == 3 and parts[1] in {"n", "a"}:
        record.setdefault("monitoring", {})["normal_interval_minutes" if parts[1] == "n" else "alert_interval_minutes"] = int(parts[2])
        save_user_data(users)
        query.answer("Interval disimpan.")
    elif len(parts) == 3 and parts[1] == "input":
        context.user_data["monitoring_input_field"] = parts[2]
        labels = {"notify_down_threshold": "minimal pelanggan down untuk mengirim notifikasi", "warning_threshold": "batas Warning ⚠️", "critical_threshold": "batas Warning 🚨"}
        query.answer()
        query.edit_message_text(f"Masukkan angka {labels[parts[2]]}. Ketik /cancel untuk membatalkan.")
        return
    elif len(parts) == 2 and parts[1] == "profiles":
        context.user_data["monitoring_input_field"] = "excluded_profiles"
        query.answer()
        query.edit_message_text("Masukkan profile PPPoE yang dikecualikan, pisahkan dengan koma.\nSaat ini: " + ", ".join(get_monitoring_config(record)["excluded_profiles"]))
        return
    else:
        record.setdefault("monitoring_state", {})["paused"] = parts[1] == "pause"
        save_user_data(users)
        query.answer("Monitoring dijeda." if parts[1] == "pause" else "Monitoring dilanjutkan.")
    query.edit_message_text(_summary(record), parse_mode="Markdown", reply_markup=_keyboard())


def handle_monitoring_input(update, context):
    field = context.user_data.get("monitoring_input_field")
    if not field:
        return False
    users = load_user_data()
    record = users.get(str(update.effective_user.id))
    if not record:
        context.user_data.pop("monitoring_input_field", None)
        return False
    value = update.effective_message.text.strip()
    if field == "excluded_profiles":
        record.setdefault("monitoring", {})[field] = [item.strip() for item in value.split(",") if item.strip()]
    else:
        try:
            value = int(value)
            if value < 1:
                raise ValueError
        except ValueError:
            update.effective_message.reply_text("Masukkan angka bulat minimal 1, atau /cancel untuk membatalkan.")
            return True
        record.setdefault("monitoring", {})[field] = value
    save_user_data(users)
    context.user_data.pop("monitoring_input_field", None)
    update.effective_message.reply_text("✅ Pengaturan monitoring disimpan.", reply_markup=_keyboard())
    return True
