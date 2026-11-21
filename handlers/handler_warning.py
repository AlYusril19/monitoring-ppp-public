def warning(update, context):
    message = "Keterangan Warning\n" \
              "⚠️ = Client Down >= 6 Users\n" \
              "🚨 = Client Down >= 12 Users\n" \
              "Harap segera dicek lebih lanjut jika muncul error ini!"
    update.message.reply_text(message)