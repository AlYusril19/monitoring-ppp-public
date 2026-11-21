"""Button-led registration and account deletion for private Telegram chats."""
from telegram import ForceReply, InlineKeyboardButton, InlineKeyboardMarkup

from configs.add_transaction import add_transaction
from configs.app_settings import get_trial_balance
from configs.data_json_user import load_user_data, save_user_data
from configs.get_current_time import get_current_time
from models.userdata import user_data_dict


def new_user_menu(update, context):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ Daftar & Mulai Trial", callback_data="onboard:register")],
    ])
    update.effective_message.reply_text(
        "Selamat datang di Monitoring MikroTik. Untuk menggunakan layanan, daftar terlebih dahulu.",
        reply_markup=keyboard)


def onboarding_callback(query, context):
    action = query.data.split(":", 1)[1]
    if action == "register":
        if str(query.from_user.id) in load_user_data():
            query.answer("Akun Anda sudah terdaftar.")
            return
        context.user_data["onboarding_step"] = "phone"
        query.answer()
        query.edit_message_text("Registrasi dimulai.")
        query.message.reply_text(
            "Masukkan nomor WhatsApp/telepon Anda untuk registrasi.\n"
            "Ketik /cancel untuk membatalkan.", reply_markup=ForceReply(selective=True))
        return
    if action == "delete_confirm":
        query.answer()
        query.edit_message_text(
            "Hapus akun beserta server, saldo, dan riwayat transaksi? Tindakan ini tidak dapat dibatalkan.",
            reply_markup=InlineKeyboardMarkup([[ 
                InlineKeyboardButton("Ya, hapus akun", callback_data="onboard:delete_now"),
                InlineKeyboardButton("Batal", callback_data="onboard:delete_cancel"),
            ]]))
        return
    if action == "delete_cancel":
        query.answer("Penghapusan dibatalkan.")
        query.edit_message_text("Penghapusan akun dibatalkan.")
        return
    if action == "delete_now":
        users = load_user_data()
        users.pop(str(query.from_user.id), None)
        save_user_data(users)
        user_data_dict.pop(query.from_user.id, None)
        context.user_data.clear()
        query.answer("Akun dihapus.")
        query.edit_message_text("Akun Anda telah dihapus. Ketik /start bila ingin membuat akun baru.")


def handle_onboarding_input(update, context):
    """Return True when a registration input was consumed."""
    if context.user_data.get("onboarding_step") != "phone":
        return False
    phone = update.effective_message.text.strip()
    if len(phone) < 8 or len(phone) > 25:
        update.effective_message.reply_text("Nomor telepon tidak valid. Masukkan kembali atau /cancel.")
        return True
    user_id = update.effective_user.id
    users = load_user_data()
    if str(user_id) in users:
        context.user_data.pop("onboarding_step", None)
        update.effective_message.reply_text("Akun sudah terdaftar.")
        return True
    trial = get_trial_balance()
    users[str(user_id)] = {
        "user_id": user_id,
        "username_telegram": update.effective_user.username or update.effective_user.full_name,
        "nohp": phone,
        "saldo": trial,
        "created_at": get_current_time(),
        "servers": [],
        "aktif": True,
        "monitoring": {},
        "monitoring_state": {},
        "account_type": "client",
    }
    save_user_data(users)
    add_transaction(user_id, trial, "trial_balance", {"trial_balance": trial})
    context.user_data.pop("onboarding_step", None)
    update.effective_message.reply_text(
        f"✅ Registrasi selesai. Anda menerima saldo trial Rp{trial:,}.\nKetik /menu untuk mulai.")
    return True
