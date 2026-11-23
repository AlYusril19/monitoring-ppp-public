"""💸 Biaya (/biaya and the button under /info).

Users get the full cost breakdown (prices + when they are charged + what is
free), using their own monitoring thresholds. Staff get prices + admin notes.
"""
from configs.app_settings import get_monitoring_config, get_price, price_summary
from configs.data_json_user import load_user_data
from configs.navigation import back_keyboard


def user_cost_text(record):
    """Rincian biaya untuk user: harga, kapan dipotong, apa yang gratis (pakai ambang user)."""
    config = get_monitoring_config(record or {})
    return (
        "💸 *Rincian Biaya*\n\n"
        f"{price_summary()}\n\n"
        "*Kapan saldo dipotong*\n"
        f"• Monitor PPPoE: setelah login router berhasil (Rp{get_price('testppp'):,}).\n"
        f"• Monitor Traffic: setelah grafik berhasil diambil (Rp{get_price('traffic'):,}).\n"
        f"• Notifikasi otomatis: saat down mencapai ⚠️ *{config['warning_threshold']}* pelanggan "
        f"(Rp{get_price('notify'):,}).\n"
        f"• Pengingat setelah jeda *{config['alert_interval_minutes']} menit* bila masih down: dipotong lagi.\n\n"
        "*Gratis*\n"
        f"• Eskalasi 🚨 (*{config['critical_threshold']}* pelanggan) selama jeda alert.\n"
        "• Pesan pulih, pengecekan rutin tanpa down, dan login router yang gagal.\n"
        "• Grafik traffic yang gagal diambil.\n\n"
        "Bila saldo habis, monitoring otomatis dijeda; lanjutkan dari ⚙️ Monitoring setelah topup.")


def staff_cost_text():
    """Daftar harga + catatan bahwa staf tidak dipotong biaya."""
    return (
        "💸 *Biaya Layanan*\n\n"
        f"{price_summary()}\n\n"
        "Akun staf tidak dipotong biaya. Ubah harga di ⚙️ Harga & Role atau /setprice.")


def biaya_fitur(update, context):
    """/biaya dan tombol 💸 Biaya (isi sesuai peran)."""
    from handlers.handler_info import is_admin_view
    user_id = update.effective_user.id
    if is_admin_view(user_id, context):
        text = staff_cost_text()
    else:
        text = user_cost_text(load_user_data().get(str(user_id)))
    update.effective_message.reply_text(text, parse_mode="Markdown",
                                        reply_markup=back_keyboard("menu:info", "⬅️ Info"))
