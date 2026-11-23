from configs.app_settings import get_monitoring_config
from configs.data_json_user import load_user_data
from configs.navigation import home_keyboard


def warning(update, context):
    """/why: arti ⚠️ Tahap 1 dan 🚨 Tahap 2 dengan nilai milik user."""
    record = load_user_data().get(str(update.effective_user.id), {})
    config = get_monitoring_config(record)
    message = (
        "*Keterangan Warning*\n\n"
        f"⚠️ *Tahap 1*: minimal *{config['warning_threshold']} pelanggan* down → notifikasi otomatis dikirim (dipotong biaya notifikasi).\n"
        f"🚨 *Tahap 2*: minimal *{config['critical_threshold']} pelanggan* down → notifikasi eskalasi, gratis selama jeda alert.\n\n"
        f"Setelah notifikasi, pengingat berikutnya dikirim setelah *{config['alert_interval_minutes']} menit* bila masih down.\n"
        "Cek PPPoE manual selalu menampilkan semua pelanggan yang down.\n"
        "Nilai dapat diubah melalui Dashboard → ⚙️ Monitoring.")
    update.effective_message.reply_text(message, parse_mode="Markdown", reply_markup=home_keyboard())
