"""Button-led registration and account deletion for private Telegram chats."""
from uuid import uuid4

from telegram import ForceReply, InlineKeyboardButton, InlineKeyboardMarkup

from configs.add_transaction import add_transaction
from configs.app_settings import get_trial_balance
from configs.data_json_user import load_app_info, load_user_data, save_app_info, save_user_data
from configs.get_current_time import get_current_time
from models.userdata import user_data_dict


def new_user_menu(update, context):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ Ajukan Registrasi", callback_data="onboard:register")],
    ])
    update.effective_message.reply_text(
        "Selamat datang di Monitoring MikroTik. Ajukan registrasi terlebih dahulu; akun aktif setelah disetujui admin.",
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
    app_info = load_app_info()
    requests = app_info.setdefault("registration_requests", {})
    if any(str(item.get("user_id")) == str(user_id) and item.get("status") == "pending"
           for item in requests.values()):
        context.user_data.pop("onboarding_step", None)
        update.effective_message.reply_text("Pengajuan registrasi Anda masih menunggu persetujuan admin.")
        return True
    request_id = uuid4().hex[:10]
    requests[request_id] = {
        "user_id": user_id,
        "username_telegram": update.effective_user.username or update.effective_user.full_name,
        "nohp": phone,
        "requested_at": get_current_time(),
        "status": "pending",
    }
    save_app_info(app_info)
    context.user_data.pop("onboarding_step", None)
    update.effective_message.reply_text(
        "✅ Pengajuan registrasi tercatat dan menunggu persetujuan admin.")
    _notify_staff_registration(context, request_id, requests[request_id])
    return True


def registration_approval_callback(query, context):
    """Approve registration with trial, without trial, or reject it."""
    from configs.app_settings import is_staff
    if not is_staff(query.from_user.id):
        query.answer("Hanya admin/operator.", show_alert=True)
        return
    _, decision, request_id = query.data.split(":", 2)
    app_info = load_app_info()
    request = app_info.get("registration_requests", {}).get(request_id)
    if not request or request.get("status") != "pending":
        query.answer("Pengajuan sudah diproses.", show_alert=True)
        return
    if decision == "reject":
        request["status"] = "rejected"
        request["processed_by"] = query.from_user.id
        request["processed_at"] = get_current_time()
        save_app_info(app_info)
        context.bot.send_message(
            request["user_id"], "❌ Pengajuan registrasi Anda ditolak. Hubungi admin bila diperlukan.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Dashboard", callback_data="nav:home")]]))
        query.answer("Pengajuan ditolak.")
        query.edit_message_text(f"Registrasi #{request_id}: ditolak.")
        return
    trial = get_trial_balance() if decision == "trial" else 0
    users = load_user_data()
    if str(request["user_id"]) in users:
        request["status"] = "duplicate"
    else:
        users[str(request["user_id"])] = {
            "user_id": request["user_id"], "username_telegram": request.get("username_telegram"),
            "nohp": request.get("nohp"), "saldo": trial, "created_at": get_current_time(),
            "servers": [], "aktif": True, "monitoring": {}, "monitoring_state": {},
            "account_type": "client",
        }
        save_user_data(users)
        # Trial is audit-only credit, never revenue; reports explicitly exclude it.
        if trial:
            add_transaction(request["user_id"], trial, "trial_balance", {"trial_balance": trial})
        request["status"] = "approved"
        request["trial_granted"] = bool(trial)
    request["processed_by"] = query.from_user.id
    request["processed_at"] = get_current_time()
    save_app_info(app_info)
    context.bot.send_message(
        request["user_id"],
        "✅ Registrasi disetujui. " + (f"Anda menerima saldo trial Rp{trial:,}. " if trial else "") + "Ketik /menu untuk mulai.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Dashboard", callback_data="nav:home")]]))
    query.answer("Registrasi disetujui.")
    query.edit_message_text(f"Registrasi #{request_id}: disetujui ({'dengan trial' if trial else 'tanpa trial'}).")


def pending_registrations_menu(query):
    app_info = load_app_info()
    pending = [(request_id, item) for request_id, item in app_info.get("registration_requests", {}).items()
               if item.get("status") == "pending"]
    if not pending:
        query.answer("Tidak ada antrian registrasi.")
        query.edit_message_text("✅ Tidak ada pengajuan registrasi yang menunggu.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Dashboard", callback_data="nav:home")]]))
        return
    keyboard = []
    for request_id, item in pending[:25]:
        name = item.get("username_telegram") or item["user_id"]
        keyboard.append([InlineKeyboardButton(f"#{request_id} · {name}", callback_data=f"reg:view:{request_id}")])
    keyboard.append([InlineKeyboardButton("🏠 Dashboard", callback_data="nav:home")])
    query.answer()
    query.edit_message_text(f"📥 Antrian registrasi ({len(pending)} menunggu):", reply_markup=InlineKeyboardMarkup(keyboard))


def registration_queue_callback(query, context):
    _, action, request_id = query.data.split(":", 2)
    if action != "view":
        return
    request = load_app_info().get("registration_requests", {}).get(request_id)
    if not request or request.get("status") != "pending":
        query.answer("Pengajuan sudah diproses.", show_alert=True)
        return
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Setujui + Trial", callback_data=f"reg:trial:{request_id}"),
        InlineKeyboardButton("✅ Tanpa Trial", callback_data=f"reg:approve:{request_id}"),
    ], [InlineKeyboardButton("❌ Tolak", callback_data=f"reg:reject:{request_id}"),
        InlineKeyboardButton("⬅️ Antrian", callback_data="admin:registrations")]])
    query.answer()
    query.edit_message_text(
        f"Registrasi #{request_id}\nUser: {request.get('username_telegram')} ({request['user_id']})\n"
        f"Telepon: {request.get('nohp')}\nDiajukan: {request.get('requested_at', '-')}", reply_markup=keyboard)


def _notify_staff_registration(context, request_id, request):
    from handlers.handler_wallet import _staff_ids
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Setujui + Trial", callback_data=f"reg:trial:{request_id}"),
        InlineKeyboardButton("✅ Tanpa Trial", callback_data=f"reg:approve:{request_id}"),
    ], [InlineKeyboardButton("❌ Tolak", callback_data=f"reg:reject:{request_id}")]])
    for staff_id in _staff_ids():
        try:
            context.bot.send_message(
                staff_id,
                f"📥 Registrasi #{request_id}\nUser: {request.get('username_telegram')} ({request['user_id']})\nTelepon: {request.get('nohp')}",
                reply_markup=keyboard)
        except Exception:
            continue
