from configs.app_settings import is_staff
from configs.data_json_user import load_user_data, save_user_data
from configs.format_rupiah import format_rupiah
from configs.add_transaction import add_transaction

def topup(update, context):
    # Mengecek apakah pengguna adalah admin yang diizinkan
    if is_staff(update.effective_user.id):
        args = context.args
        if len(args) == 2:
            user_id = int(args[0])
            amount = int(args[1])
            user_data = load_user_data()
            # Memeriksa apakah pengguna sudah ada dalam data
            if str(user_id) in user_data:
                # Menambahkan jumlah top-up baru ke saldo yang ada
                user_data[str(user_id)]["saldo"] += amount
                # Mengirimkan notifikasi saldo masuk ke pengguna
                saldo = user_data[str(user_id)]['saldo']
                saldo_format = format_rupiah(saldo)  # Format saldo menjadi IDR
                context.bot.send_message(chat_id=user_id, text=f"Saldo Anda telah bertambah sebesar {format_rupiah(amount)}. Saldo saat ini: {saldo_format}")
            else:
                # Cek user jika pengguna belum ada
                context.bot.send_message(chat_id=update.effective_chat.id, text="Data User tidak ditemukan.")
                return
            # Menyimpan perubahan data pengguna
            save_user_data(user_data)
            add_transaction(user_id, amount, "topup")
            # Mengirimkan pesan konfirmasi top-up saldo ke admin
            context.bot.send_message(chat_id=update.effective_chat.id, text=f"Top-up saldo berhasil. Saldo {user_id} sekarang: {saldo_format}")
        else:
            # Mengirimkan pesan jika format argumen tidak sesuai
            context.bot.send_message(chat_id=update.effective_chat.id, text="Format yang benar: /topup <user_id> <amount>")
    else:
        # Mengirimkan pesan jika pengguna bukan admin yang diizinkan
        context.bot.send_message(chat_id=update.effective_chat.id, text="Akses ditolak.")
