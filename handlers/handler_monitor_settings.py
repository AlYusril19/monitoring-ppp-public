from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from configs.app_settings import get_monitoring_config, parse_quiet_hours, quiet_hours_label
from configs.data_json_user import load_user_data, save_user_data
from configs.navigation import cancel_keyboard, home_keyboard


def _keyboard():
    """Keyboard menu ⚙️ Monitoring."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Cek 10m", callback_data="mon:n:10"), InlineKeyboardButton("Cek 20m", callback_data="mon:n:20"), InlineKeyboardButton("Cek 30m", callback_data="mon:n:30")],
        [InlineKeyboardButton("Jeda 60m", callback_data="mon:a:60"), InlineKeyboardButton("Jeda 120m", callback_data="mon:a:120"), InlineKeyboardButton("Jeda 240m", callback_data="mon:a:240")],
        [InlineKeyboardButton("⚠️ Tahap 1", callback_data="mon:input:warning_threshold"), InlineKeyboardButton("🚨 Tahap 2", callback_data="mon:input:critical_threshold")],
        [InlineKeyboardButton("👥 Profile Dikecualikan", callback_data="mon:profiles"),
         InlineKeyboardButton("🌙 Jam Senyap", callback_data="mon:quiet")],
        [InlineKeyboardButton("▶ Lanjutkan", callback_data="mon:resume"), InlineKeyboardButton("⏸ Jeda", callback_data="mon:pause")],
        [InlineKeyboardButton("🏠 Dashboard", callback_data="nav:home")],
    ])


def _summary(record):
    """Ringkasan pengaturan monitoring user (Markdown)."""
    config = get_monitoring_config(record)
    status = "dijeda" if record.get("monitoring_state", {}).get("paused") else "aktif"
    global_profiles = ", ".join(config["global_excluded_profiles"]) or "tidak ada"
    user_profiles = ", ".join(config["user_excluded_profiles"]) or "tidak ada"
    return (
        "⚙️ *Pengaturan Monitoring*\n"
        f"Cek router setiap: *{config['normal_interval_minutes']} menit*\n"
        f"⚠️ Tahap 1 (notif otomatis): *≥ {config['warning_threshold']} pelanggan down*\n"
        f"🚨 Tahap 2 (eskalasi, gratis): *≥ {config['critical_threshold']} pelanggan down*\n"
        f"Jeda alert: *{config['alert_interval_minutes']} menit* (setelah itu notif diulang & dipotong bila masih down)\n"
        f"Profile dikecualikan (admin): `{global_profiles}`\n"
        f"Profile dikecualikan (Anda): `{user_profiles}`\n"
        f"🌙 Jam senyap: *{quiet_hours_label(config['quiet_hours'])}* (tanpa cek, notifikasi, & biaya)\n"
        f"Status: *{status}*")


def monitoring_settings(update, context):
    """/monitoring dan tombol ⚙️ Monitoring."""
    users = load_user_data()
    record = users.get(str(update.effective_user.id))
    if not record:
        update.effective_message.reply_text("Anda belum terdaftar.", reply_markup=home_keyboard())
        return
    update.effective_message.reply_text(_summary(record), parse_mode="Markdown", reply_markup=_keyboard())


def monitoring_callback(query, context):
    """Tombol mon:* (interval, jeda, ambang, profile, pause/resume)."""
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
        labels = {"warning_threshold": "pelanggan down untuk ⚠️ Tahap 1 (notifikasi otomatis)",
                  "critical_threshold": "pelanggan down untuk 🚨 Tahap 2 (eskalasi)"}
        if parts[2] not in labels:
            query.answer("Pengaturan ini sudah tidak dipakai.", show_alert=True)
            return
        context.user_data["monitoring_input_field"] = parts[2]
        query.answer()
        query.edit_message_text(f"Masukkan angka {labels[parts[2]]}. Ketik /cancel untuk membatalkan.",
                                reply_markup=cancel_keyboard())
        return
    elif len(parts) == 2 and parts[1] == "quiet":
        context.user_data["monitoring_input_field"] = "quiet_hours"
        query.answer()
        query.edit_message_text(
            "🌙 *Jam Senyap*\nSelama jam ini monitoring otomatis tidak mengecek router, tidak mengirim "
            "notifikasi, dan tidak memotong saldo. Setelah jam senyap selesai, pengecekan berjalan lagi.\n\n"
            "Ketik rentang jam format 24 jam `HH:MM-HH:MM`, contoh `22:00-06:00`.\n"
            "Ketik `-` untuk menonaktifkan. /cancel untuk membatalkan.\n\n"
            f"Saat ini: *{quiet_hours_label(get_monitoring_config(record)['quiet_hours'])}*",
            parse_mode="Markdown", reply_markup=cancel_keyboard())
        return
    elif len(parts) == 2 and parts[1] == "profiles":
        context.user_data["monitoring_input_field"] = "excluded_profiles"
        query.answer()
        config = get_monitoring_config(record)
        query.edit_message_text(
            "Masukkan profile PPPoE tambahan yang ingin Anda kecualikan, pisahkan dengan koma.\n"
            "Ketik `-` untuk mengosongkan. /cancel untuk membatalkan.\n\n"
            f"Sudah dikecualikan oleh admin: {', '.join(config['global_excluded_profiles']) or 'tidak ada'}\n"
            f"Tambahan Anda saat ini: {', '.join(config['user_excluded_profiles']) or 'tidak ada'}",
            reply_markup=cancel_keyboard())
        return
    else:
        record.setdefault("monitoring_state", {})["paused"] = parts[1] == "pause"
        save_user_data(users)
        query.answer("Monitoring dijeda." if parts[1] == "pause" else "Monitoring dilanjutkan.")
    query.edit_message_text(_summary(record), parse_mode="Markdown", reply_markup=_keyboard())


def handle_monitoring_input(update, context):
    """Form angka ambang ⚠️/🚨 atau daftar profile tambahan user."""
    field = context.user_data.get("monitoring_input_field")
    if not field:
        return False
    users = load_user_data()
    record = users.get(str(update.effective_user.id))
    if not record:
        context.user_data.pop("monitoring_input_field", None)
        return False
    value = update.effective_message.text.strip()
    if field == "quiet_hours":
        try:
            quiet = parse_quiet_hours(value)
        except ValueError as exc:
            update.effective_message.reply_text(f"{exc}\nMasukkan ulang atau /cancel.", parse_mode="Markdown",
                                                reply_markup=cancel_keyboard())
            return True
        if quiet:
            record.setdefault("monitoring", {})["quiet_hours"] = quiet
        else:
            record.setdefault("monitoring", {}).pop("quiet_hours", None)
    elif field == "excluded_profiles":
        # Stores only the user's extra profiles; the admin list is applied on top.
        record.setdefault("monitoring", {})[field] = [] if value == "-" else [
            item.strip() for item in value.split(",") if item.strip()]
    else:
        try:
            value = int(value)
            if value < 1:
                raise ValueError
        except ValueError:
            update.effective_message.reply_text("Masukkan angka bulat minimal 1, atau /cancel untuk membatalkan.",
                                                reply_markup=cancel_keyboard())
            return True
        current = get_monitoring_config(record)
        if field == "warning_threshold" and value >= current["critical_threshold"]:
            update.effective_message.reply_text(
                f"⚠️ Tahap 1 harus lebih kecil dari 🚨 Tahap 2 ({current['critical_threshold']}). Masukkan ulang atau /cancel.",
                reply_markup=cancel_keyboard())
            return True
        if field == "critical_threshold" and value <= current["warning_threshold"]:
            update.effective_message.reply_text(
                f"🚨 Tahap 2 harus lebih besar dari ⚠️ Tahap 1 ({current['warning_threshold']}). Masukkan ulang atau /cancel.",
                reply_markup=cancel_keyboard())
            return True
        record.setdefault("monitoring", {})[field] = value
        record["monitoring"].pop("notify_down_threshold", None)
    save_user_data(users)
    context.user_data.pop("monitoring_input_field", None)
    # Show the updated settings right away so the user does not have to reopen ⚙️ Monitoring.
    update.effective_message.reply_text(f"✅ Pengaturan monitoring disimpan.\n\n{_summary(record)}",
                                        parse_mode="Markdown", reply_markup=_keyboard())
    return True
