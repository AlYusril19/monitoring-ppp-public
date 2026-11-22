"""Wallet request and staff approval flow, including photo proof metadata."""
from datetime import datetime
from uuid import uuid4

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from configs.add_transaction import add_transaction
from configs.app_settings import is_staff
from configs.app_settings import get_qris_file_id, set_qris_file_id, is_superadmin
from configs.data_json_user import load_app_info, load_user_data, save_app_info, save_user_data
from configs.format_rupiah import format_rupiah
from configs.navigation import home_keyboard


AMOUNTS = (5000, 10000, 25000, 50000, 100000)


def wallet_menu(update, context):
    keyboard = [[InlineKeyboardButton(f"Rp{amount:,}", callback_data=f"wallet:amount:{amount}")]
                for amount in AMOUNTS]
    keyboard.append([InlineKeyboardButton("🏠 Dashboard", callback_data="nav:home")])
    record = load_user_data().get(str(update.effective_user.id), {})
    balance = int(record.get("saldo", 0))
    qris_file_id = get_qris_file_id()
    if qris_file_id:
        context.bot.send_photo(
            chat_id=update.effective_chat.id, photo=qris_file_id,
            caption="Scan QRIS berikut, lalu pilih nominal dan kirim bukti transfer.")
    update.effective_message.reply_text(
        f"💳 *Saldo Anda: Rp{balance:,}*\n\nPilih nominal, lalu kirim foto bukti transfer.",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


def wallet_callback(query, context):
    parts = query.data.split(":")
    if len(parts) != 3 or parts[1] != "amount":
        return
    amount = int(parts[2])
    context.user_data["pending_topup_amount"] = amount
    query.answer()
    query.edit_message_text(
        f"Nominal: Rp{amount:,}. Kirim *foto bukti transfer* sekarang.\n"
        "Ketik /cancel untuk membatalkan.", parse_mode="Markdown")


def capture_payment_proof(update, context):
    if context.user_data.pop("qris_upload", False):
        if not is_superadmin(update.effective_user.id):
            return
        set_qris_file_id(update.effective_message.photo[-1].file_id)
        update.effective_message.reply_text("✅ QRIS disimpan dan akan tampil saat user mengisi saldo.")
        return
    amount = context.user_data.get("pending_topup_amount")
    if not amount:
        return
    user_id = update.effective_user.id
    users = load_user_data()
    if str(user_id) not in users:
        update.effective_message.reply_text("Anda belum terdaftar.")
        context.user_data.pop("pending_topup_amount", None)
        return

    request_id = uuid4().hex[:10]
    app_info = load_app_info()
    requests = app_info.setdefault("topup_requests", {})
    requests[request_id] = {
        "user_id": user_id,
        "amount": amount,
        "proof_file_id": update.effective_message.photo[-1].file_id,
        "requested_at": datetime.utcnow().isoformat(),
        "status": "pending",
    }
    save_app_info(app_info)
    context.user_data.pop("pending_topup_amount", None)
    update.effective_message.reply_text(
        f"✅ Permintaan #{request_id} tercatat dan menunggu persetujuan admin.")

    keyboard = InlineKeyboardMarkup([[ 
        InlineKeyboardButton("✅ Setujui", callback_data=f"topup:approve:{request_id}"),
        InlineKeyboardButton("❌ Tolak", callback_data=f"topup:reject:{request_id}"),
    ]])
    for staff_id in _staff_ids():
        try:
            context.bot.send_photo(
                chat_id=staff_id, photo=update.effective_message.photo[-1].file_id,
                caption=(f"Permintaan saldo #{request_id}\nUser: {user_id}\n"
                         f"Nominal: Rp{amount:,}"), reply_markup=keyboard)
        except Exception:
            # A staff account may not have opened the bot yet; approval remains
            # available through the request id rather than losing the request.
            continue


def topup_approval_callback(query, context):
    if not is_staff(query.from_user.id):
        query.answer("Hanya admin/operator.", show_alert=True)
        return
    _, decision, request_id = query.data.split(":", 2)
    app_info = load_app_info()
    request = app_info.get("topup_requests", {}).get(request_id)
    if not request or request.get("status") != "pending":
        query.answer("Permintaan sudah diproses.", show_alert=True)
        return

    request["status"] = "approved" if decision == "approve" else "rejected"
    request["processed_by"] = query.from_user.id
    request["processed_at"] = datetime.utcnow().isoformat()
    if decision == "approve":
        users = load_user_data()
        record = users.get(str(request["user_id"]))
        if not record:
            query.answer("User tidak ditemukan.", show_alert=True)
            return
        record["saldo"] = int(record.get("saldo", 0)) + int(request["amount"])
        save_user_data(users)
        add_transaction(request["user_id"], int(request["amount"]), "topup_request",
                        {"request_id": request_id, "approved_by": query.from_user.id})
        context.bot.send_message(
            request["user_id"],
            f"✅ Permintaan saldo #{request_id} disetujui. Saldo bertambah {format_rupiah(request['amount'])}.",
            reply_markup=home_keyboard())
    else:
        context.bot.send_message(
            request["user_id"], f"❌ Permintaan saldo #{request_id} ditolak.", reply_markup=home_keyboard())
    save_app_info(app_info)
    query.answer("Permintaan diproses.")
    result = f"Permintaan #{request_id}: {request['status']}."
    if query.message.photo:
        query.edit_message_caption(caption=result)
    else:
        query.edit_message_text(result, reply_markup=home_keyboard())


def pending_topups_menu(query):
    """Persistent queue view: approvals remain available after notifications scroll away."""
    app_info = load_app_info()
    pending = [(request_id, item) for request_id, item in app_info.get("topup_requests", {}).items()
               if item.get("status") == "pending"]
    if not pending:
        query.answer("Tidak ada antrian topup.")
        query.edit_message_text("✅ Tidak ada permintaan topup yang menunggu persetujuan.", reply_markup=home_keyboard())
        return
    keyboard = []
    for request_id, item in pending[:25]:
        keyboard.append([InlineKeyboardButton(
            f"#{request_id} · {item['user_id']} · Rp{int(item['amount']):,}",
            callback_data=f"topup:view:{request_id}")])
    keyboard.append([InlineKeyboardButton("🏠 Dashboard", callback_data="nav:home")])
    query.answer()
    query.edit_message_text(f"⏳ Antrian topup ({len(pending)} menunggu):", reply_markup=InlineKeyboardMarkup(keyboard))


def topup_queue_callback(query, context):
    _, action, request_id = query.data.split(":", 2)
    if action != "view":
        return
    request = load_app_info().get("topup_requests", {}).get(request_id)
    if not request or request.get("status") != "pending":
        query.answer("Permintaan sudah diproses.", show_alert=True)
        return
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Setujui", callback_data=f"topup:approve:{request_id}"),
        InlineKeyboardButton("❌ Tolak", callback_data=f"topup:reject:{request_id}"),
    ], [InlineKeyboardButton("⬅️ Kembali ke Antrian", callback_data="admin:topups")]])
    query.answer()
    query.edit_message_text(
        f"Permintaan topup #{request_id}\nUser: {request['user_id']}\nNominal: Rp{int(request['amount']):,}\n"
        f"Diajukan: {request.get('requested_at', '-')}", reply_markup=keyboard)


def begin_manual_topup(query, context):
    context.user_data["manual_topup_step"] = "user_id"
    query.answer()
    query.edit_message_text(
        "Masukkan Telegram User ID penerima saldo.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✖️ Batal", callback_data="admin:manualcancel")]]))


def handle_manual_topup_input(update, context):
    """Consume admin's two-step manual credit input. Return True if consumed."""
    step = context.user_data.get("manual_topup_step")
    if not step:
        return False
    if not is_staff(update.effective_user.id):
        context.user_data.pop("manual_topup_step", None)
        return False
    value = update.effective_message.text.strip()
    if step == "user_id":
        users = load_user_data()
        if not value.isdigit() or value not in users:
            update.effective_message.reply_text("User ID tidak ditemukan. Masukkan ulang atau /cancel.")
            return True
        context.user_data["manual_topup_user_id"] = value
        context.user_data["manual_topup_step"] = "amount"
        update.effective_message.reply_text(f"Masukkan nominal saldo untuk user {value}.")
        return True
    try:
        amount = int(value)
        if amount <= 0:
            raise ValueError
    except ValueError:
        update.effective_message.reply_text("Nominal harus berupa angka lebih dari nol. Masukkan ulang atau /cancel.")
        return True
    user_id = context.user_data.pop("manual_topup_user_id")
    context.user_data.pop("manual_topup_step", None)
    users = load_user_data()
    record = users.get(user_id)
    if not record:
        update.effective_message.reply_text("User sudah tidak ditemukan.")
        return True
    record["saldo"] = int(record.get("saldo", 0)) + amount
    save_user_data(users)
    add_transaction(int(user_id), amount, "manual_topup", {"credited_by": update.effective_user.id})
    context.bot.send_message(
        int(user_id),
        f"✅ Saldo manual bertambah {format_rupiah(amount)}. Saldo sekarang: {format_rupiah(record['saldo'])}.",
        reply_markup=home_keyboard())
    update.effective_message.reply_text(
        f"✅ Saldo user {user_id} ditambah {format_rupiah(amount)}. Saldo kini {format_rupiah(record['saldo'])}.",
        reply_markup=home_keyboard())
    return True


def _staff_ids():
    settings = load_app_info().get("settings", {})
    roles = settings.get("roles", {})
    from configs.send_message import allowed_admin_ids
    return set(allowed_admin_ids) | {int(uid) for uid, role in roles.items() if role in {"admin", "operator"}}


def set_qris_command(update, context):
    if not is_superadmin(update.effective_user.id):
        update.effective_message.reply_text("Hanya superadmin yang dapat mengganti QRIS.")
        return
    context.user_data["qris_upload"] = True
    update.effective_message.reply_text("Kirim foto QRIS sekarang. Foto berikutnya akan dipakai sebagai QRIS topup.")
