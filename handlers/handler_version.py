from dotenv import load_dotenv
import os

load_dotenv()

def version_command_handler(update, context):
    app_version = os.environ.get('APP_VERSION')
    released = os.environ.get('RELEASED')
    email = os.environ.get('EMAIL')
    message = f"Bot Version {app_version} (Released in {released})\n" \
                "Fitur tersedia\n" \
                "   - Dashboard tombol User dan Admin\n" \
                "   - Registrasi ber-antrian, pilihan trial, QRIS, dan approval topup\n" \
                "   - Server tersimpan dan Server Custom sementara\n" \
                "   - Tes PPPoE dan monitoring otomatis dengan interval, threshold, warning, serta profile pengecualian per user\n" \
                "   - Traffic berdasarkan Tools > Graphing beserta komentar interface\n" \
                "   - Laporan pendapatan bulanan dan tahunan\n" \
                "   - Harga fitur dan role admin/operator\n\n" \
                "Update 2.2.1\n" \
                "   - Threshold notifikasi, Warning ⚠️/🚨, kelola server, dan dokumentasi pengembangan diperbarui.\n\n" \
                f"Develop by SkyTaMa {email}"
    update.message.reply_text(message)
