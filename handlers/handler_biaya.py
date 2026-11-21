from configs.app_settings import get_price


def biaya_fitur(update, context):
    message = f"Berikut adalah biaya layanan tiap fitur\n\n" \
              f"- Cek PPPOE = Rp{get_price('testppp'):,}\n" \
              f"- Cek Traffic = Rp{get_price('traffic'):,}\n" \
              f"- Notifikasi down = Rp{get_price('notify'):,}\n\n"\
              "Biaya dipotong hanya setelah koneksi/proses berhasil."
    update.message.reply_text(message)
