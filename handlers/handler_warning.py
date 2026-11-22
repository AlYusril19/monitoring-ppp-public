from configs.app_settings import get_monitoring_config
from configs.data_json_user import load_user_data
from configs.navigation import home_keyboard


def warning(update, context):
    record = load_user_data().get(str(update.effective_user.id), {})
    config = get_monitoring_config(record)
    message = (
        "*Keterangan Warning*\n\n"
        f"⚠️ Warning muncul saat minimal *{config['warning_threshold']} pelanggan* down.\n"
        f"🚨 Warning kritis muncul saat minimal *{config['critical_threshold']} pelanggan* down.\n\n"
        f"Notifikasi otomatis baru dikirim jika minimal *{config['notify_down_threshold']} pelanggan* down.\n"
        "Nilai dapat diubah sendiri melalui Dashboard → Monitoring.")
    update.effective_message.reply_text(message, parse_mode="Markdown", reply_markup=home_keyboard())
