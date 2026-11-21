from configs.app_settings import get_role, get_price, is_superadmin, load_settings, set_price, set_role, set_trial_balance
from configs.send_message import send_message


FEATURES = {"testppp", "traffic", "notify"}


def settings_command(update, context):
    settings = load_settings()
    role = get_role(update.effective_user.id)
    prices = settings["prices"]
    update.effective_message.reply_text(
        "⚙️ Pengaturan layanan\n"
        f"Role Anda: {role}\n"
        f"Test PPPoE: Rp{prices['testppp']}\n"
        f"Traffic: Rp{prices['traffic']}\n"
        f"Notifikasi down: Rp{prices['notify']}\n\n"
        "Superadmin: /setprice <testppp|traffic|notify> <nominal>\n"
        "Superadmin: /setrole <user_id> <operator|admin|user>\n"
        "Superadmin: /settrial <nominal>")


def set_price_command(update, context):
    if not is_superadmin(update.effective_user.id):
        update.effective_message.reply_text("Hanya superadmin yang dapat mengubah harga.")
        return
    if len(context.args) != 2 or context.args[0] not in FEATURES:
        update.effective_message.reply_text("Gunakan: /setprice <testppp|traffic|notify> <nominal>")
        return
    try:
        amount = int(context.args[1])
        if amount < 0:
            raise ValueError
    except ValueError:
        update.effective_message.reply_text("Nominal harus berupa angka positif.")
        return
    feature = context.args[0]
    previous_amount = get_price(feature)
    set_price(feature, amount)
    update.effective_message.reply_text(
        f"Harga {feature} diperbarui.\n"
        f"Harga sebelumnya: Rp{previous_amount:,}\n"
        f"Harga baru: Rp{amount:,}")


def set_role_command(update, context):
    if not is_superadmin(update.effective_user.id):
        update.effective_message.reply_text("Hanya superadmin yang dapat mengatur role.")
        return
    if len(context.args) != 2:
        update.effective_message.reply_text("Gunakan: /setrole <user_id> <operator|admin|user>")
        return
    try:
        set_role(int(context.args[0]), context.args[1].lower())
    except ValueError as exc:
        update.effective_message.reply_text(str(exc))
        return
    update.effective_message.reply_text("Role disimpan.")


def set_trial_command(update, context):
    if not is_superadmin(update.effective_user.id):
        update.effective_message.reply_text("Hanya superadmin yang dapat mengubah saldo trial.")
        return
    if len(context.args) != 1:
        update.effective_message.reply_text("Gunakan: /settrial <nominal>")
        return
    try:
        amount = int(context.args[0])
        if amount < 0:
            raise ValueError
    except ValueError:
        update.effective_message.reply_text("Nominal harus berupa angka nol atau positif.")
        return
    set_trial_balance(amount)
    update.effective_message.reply_text(f"Saldo trial pendaftaran baru disimpan: Rp{amount:,}.")
