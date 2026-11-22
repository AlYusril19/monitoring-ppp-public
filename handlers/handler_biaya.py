from configs.app_settings import get_price
from configs.navigation import home_keyboard


def biaya_fitur(update, context):
    message = (
        "*Biaya Layanan Saat Ini*\n\n"
        f"- Cek PPPoE: *Rp{get_price('testppp'):,}*\n"
        f"- Monitor Traffic: *Rp{get_price('traffic'):,}*\n"
        f"- Notifikasi down: *Rp{get_price('notify'):,}*\n\n"
        "Biaya dipotong hanya setelah koneksi/proses berhasil.")
    update.effective_message.reply_text(message, parse_mode="Markdown", reply_markup=home_keyboard())
