"""Button-led registration and account deletion for private Telegram chats.

Anti mass-registration (trial abuse):
  * The phone number must be shared with Telegram's "📱 Kirim Nomor Saya"
    button; the contact must belong to the same Telegram account, so a number
    cannot be typed or borrowed.
  * One trial per phone number and per Telegram account, ever. The record
    (app_info.trial_registry) survives account deletion.
  * A number already used by another account is flagged to the admin and gets
    no trial.
  * Global limit of new requests per hour and a cooldown after rejection
    (Dashboard Admin → 👥 Data User → 🎁 Trial & Registrasi).
"""
import re
from datetime import datetime, timedelta
from uuid import uuid4

from telegram import (InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup,
                      ReplyKeyboardRemove)

from configs.add_transaction import add_transaction
from configs.app_settings import (get_registration_limits, get_trial_balance, get_trial_mode, is_staff,
                                  staff_ids)
from configs.chat_tracker import mark_input_consumed
from configs.data_json_user import load_app_info, load_user_data, save_app_info, save_user_data
from configs.get_current_time import get_current_time
from configs.navigation import back_keyboard, cancel_keyboard, home_keyboard

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


# ---------------------------------------------------------------- helpers
def normalize_phone(text):
    """Nomor telepon -> hanya digit berawalan 62 (08xx / 8xx / +62xx dianggap sama)."""
    digits = re.sub(r"\D", "", str(text or ""))
    if digits.startswith("0"):
        digits = "62" + digits[1:]
    elif digits.startswith("8"):
        digits = "62" + digits
    return digits


def _hours_since(text):
    """Jam sejak waktu 'YYYY-mm-dd HH:MM:SS' (WIB); angka besar bila tidak valid."""
    try:
        then = datetime.strptime(text, TIME_FORMAT)
    except (TypeError, ValueError):
        return 10 ** 6
    now = datetime.strptime(get_current_time(), TIME_FORMAT)
    return (now - then) / timedelta(hours=1)


def remove_reply_keyboard(bot, chat_id):
    """Tutup tombol 📱 Kirim Nomor (reply keyboard) tanpa meninggalkan pesan."""
    try:
        message = bot.send_message(chat_id=chat_id, text="⌛", reply_markup=ReplyKeyboardRemove(),
                                   disable_notification=True)
        bot.delete_message(chat_id=chat_id, message_id=message.message_id)
    except Exception as exc:
        print(f"Gagal menutup keyboard kontak {chat_id}: {exc}")


def registration_block_reason(user_id, app_info=None):
    """Alasan user belum boleh mengajukan registrasi, atau None bila boleh."""
    app_info = app_info if app_info is not None else load_app_info()
    requests = app_info.get("registration_requests", {}).values()
    limits = get_registration_limits()
    own = [item for item in requests if str(item.get("user_id")) == str(user_id)]
    if any(item.get("status") == "pending" for item in own):
        return "Pengajuan registrasi Anda masih menunggu persetujuan admin."
    cooldown = limits["reject_cooldown_hours"]
    rejected = [item for item in own if item.get("status") == "rejected"]
    if cooldown and rejected:
        waited = min(_hours_since(item.get("processed_at")) for item in rejected)
        if waited < cooldown:
            return f"Pengajuan Anda sebelumnya ditolak. Coba lagi dalam {int(cooldown - waited) + 1} jam."
    hourly = limits["hourly_limit"]
    if hourly and sum(1 for item in requests if _hours_since(item.get("requested_at")) < 1) >= hourly:
        return "Pendaftaran sedang ramai. Silakan coba lagi sekitar 1 jam lagi."
    return None


def trial_block_reason(user_id, phone, app_info=None, users=None):
    """Alasan trial tidak boleh diberikan, atau None bila memenuhi syarat."""
    if get_trial_mode() == "off" or get_trial_balance() <= 0:
        return "trial dinonaktifkan admin"
    app_info = app_info if app_info is not None else load_app_info()
    registry = app_info.get("trial_registry", {})
    if str(user_id) in registry.get("user_ids", {}):
        return "akun Telegram ini sudah pernah menerima trial"
    phone = normalize_phone(phone)
    if phone and phone in registry.get("phones", {}):
        return "nomor ini sudah pernah menerima trial"
    users = users if users is not None else load_user_data()
    for uid, record in users.items():
        if uid != str(user_id) and phone and normalize_phone(record.get("nohp")) == phone:
            return f"nomor ini sudah dipakai akun lain (ID {uid})"
    return None


def _remember_trial(app_info, user_id, phone, amount):
    """Catat penerima trial agar nomor/akun yang sama tidak mendapat trial lagi."""
    registry = app_info.setdefault("trial_registry", {"phones": {}, "user_ids": {}})
    now = get_current_time()
    registry.setdefault("user_ids", {})[str(user_id)] = now
    phone = normalize_phone(phone)
    if phone:
        registry.setdefault("phones", {})[phone] = {"user_id": user_id, "at": now, "amount": amount}


# ---------------------------------------------------------------- user side
def new_user_menu(update, context):
    """Pesan sambutan + tombol ✨ Ajukan Registrasi untuk user baru."""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ Ajukan Registrasi", callback_data="onboard:register")],
    ])
    update.effective_message.reply_text(
        "Selamat datang di Monitoring MikroTik. Ajukan registrasi terlebih dahulu; akun aktif setelah disetujui admin.",
        reply_markup=keyboard)


def onboarding_callback(query, context):
    """Tombol onboard:* (mulai registrasi, hapus akun)."""
    action = query.data.split(":", 1)[1]
    if action == "register":
        _start_registration(query, context)
        return
    if action == "delete_confirm":
        from handlers.handler_refund import deletion_notice, refund_quote
        quote = refund_quote(query.from_user.id)
        if quote is None:
            query.answer("Anda belum terdaftar.", show_alert=True)
            return
        query.answer()
        query.edit_message_text(
            "🗑 *Hapus Akun*\nServer, saldo, dan riwayat transaksi akan dihapus. "
            "Tindakan ini tidak dapat dibatalkan.\n\n" + deletion_notice(quote),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Ya, hapus akun", callback_data="onboard:delete_now"),
                InlineKeyboardButton("Batal", callback_data="onboard:delete_cancel"),
            ]]))
        return
    if action == "delete_cancel":
        query.answer("Penghapusan dibatalkan.")
        query.edit_message_text("Penghapusan akun dibatalkan.", reply_markup=home_keyboard())
        return
    if action == "delete_now":
        from handlers.handler_refund import delete_account, deletion_result_text
        result = delete_account(context.bot, query.from_user.id)
        context.user_data.clear()
        if result is None:
            query.answer("Akun sudah tidak ada.", show_alert=True)
            return
        query.answer("Akun dihapus.")
        query.edit_message_text(deletion_result_text(result, by_admin=False), parse_mode="Markdown",
                                reply_markup=home_keyboard("✨ Mulai lagi"))


def _start_registration(query, context):
    """onboard:register: cek batas, lalu minta nomor lewat tombol kontak Telegram."""
    user_id = query.from_user.id
    if str(user_id) in load_user_data():
        query.answer("Akun Anda sudah terdaftar.")
        return
    reason = registration_block_reason(user_id)
    if reason:
        query.answer()
        query.edit_message_text(reason, reply_markup=home_keyboard())
        return
    context.user_data["onboarding_step"] = "contact"
    query.answer()
    query.edit_message_text(
        "✨ *Registrasi*\nTekan tombol *📱 Kirim Nomor Saya* di bawah layar untuk membagikan nomor akun "
        "Telegram Anda. Nomor diverifikasi oleh Telegram dan tidak bisa diketik manual.\n"
        "Ketik /cancel atau tekan ✖️ Batal untuk membatalkan.",
        parse_mode="Markdown", reply_markup=cancel_keyboard())
    context.bot.send_message(
        chat_id=query.message.chat_id, text="👇 Bagikan nomor Anda:",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("📱 Kirim Nomor Saya", request_contact=True)]],
                                         resize_keyboard=True, one_time_keyboard=True))


def handle_onboarding_input(update, context):
    """Teks saat registrasi menunggu kontak: arahkan ke tombol (nomor ketikan tidak diterima)."""
    if context.user_data.get("onboarding_step") is None:
        return False
    update.effective_message.reply_text(
        "Nomor tidak bisa diketik. Tekan tombol *📱 Kirim Nomor Saya* di bawah layar, atau /cancel.",
        parse_mode="Markdown", reply_markup=cancel_keyboard())
    return True


def handle_contact(update, context):
    """Kontak dibagikan (tombol 📱 Kirim Nomor Saya): buat pengajuan registrasi terverifikasi."""
    message = update.effective_message
    user = update.effective_user
    contact = getattr(message, "contact", None)
    if contact is None or str(user.id) in load_user_data():
        return
    mark_input_consumed()
    context.user_data.pop("onboarding_step", None)
    remove_reply_keyboard(context.bot, message.chat_id)
    if getattr(contact, "user_id", None) != user.id:
        message.reply_text("❌ Nomor harus milik akun Telegram ini. Gunakan tombol 📱 Kirim Nomor Saya, "
                           "jangan meneruskan kontak orang lain.", reply_markup=home_keyboard())
        return
    app_info = load_app_info()
    reason = registration_block_reason(user.id, app_info)
    if reason:
        message.reply_text(reason, reply_markup=home_keyboard())
        return
    phone = normalize_phone(contact.phone_number)
    users = load_user_data()
    request_id = uuid4().hex[:10]
    request = {
        "user_id": user.id,
        "username_telegram": user.username or user.full_name,
        "nohp": phone,
        "phone_verified": True,
        "requested_at": get_current_time(),
        "status": "pending",
        "trial_block_reason": trial_block_reason(user.id, phone, app_info, users),
    }
    app_info.setdefault("registration_requests", {})[request_id] = request
    save_app_info(app_info)
    message.reply_text("✅ Pengajuan registrasi tercatat dan menunggu persetujuan admin.",
                       reply_markup=home_keyboard())
    _notify_staff_registration(context, request_id, request)


# ---------------------------------------------------------------- staff side
def _approval_keyboard(request_id, request, with_back=False):
    """Tombol keputusan sesuai mode trial dan kelayakan trial pengajuan ini."""
    eligible = not trial_block_reason(request["user_id"], request.get("nohp"))
    mode = get_trial_mode()
    if mode == "manual" and eligible:
        first = [InlineKeyboardButton("✅ Setujui + Trial", callback_data=f"reg:trial:{request_id}"),
                 InlineKeyboardButton("✅ Tanpa Trial", callback_data=f"reg:approve:{request_id}")]
    else:
        label = "✅ Setujui + Trial" if mode == "auto" and eligible else "✅ Setujui"
        first = [InlineKeyboardButton(label, callback_data=f"reg:approve:{request_id}")]
    second = [InlineKeyboardButton("❌ Tolak", callback_data=f"reg:reject:{request_id}")]
    if with_back:
        second.append(InlineKeyboardButton("⬅️ Antrian", callback_data="admin:registrations"))
    return InlineKeyboardMarkup([first, second])


def _request_text(request_id, request):
    """Ringkasan pengajuan untuk staf, termasuk tanda risiko."""
    verified = "✅ terverifikasi Telegram" if request.get("phone_verified") else "⚠️ diketik manual (data lama)"
    reason = trial_block_reason(request["user_id"], request.get("nohp"))
    trial = f"⚠️ Tidak dapat trial: {reason}" if reason else f"🎁 Layak trial Rp{get_trial_balance():,}"
    return (f"📥 Registrasi #{request_id}\nUser: {request.get('username_telegram')} ({request['user_id']})\n"
            f"Telepon: {request.get('nohp')} ({verified})\nDiajukan: {request.get('requested_at', '-')}\n{trial}")


def registration_approval_callback(query, context):
    """Approve registration (with trial when allowed), or reject it."""
    if not is_staff(query.from_user.id):
        query.answer("Hanya admin/operator.", show_alert=True)
        return
    _, decision, request_id = query.data.split(":", 2)
    app_info = load_app_info()
    request = app_info.get("registration_requests", {}).get(request_id)
    if not request or request.get("status") != "pending":
        query.answer("Pengajuan sudah diproses.", show_alert=True)
        return
    request["processed_by"] = query.from_user.id
    request["processed_at"] = get_current_time()
    if decision == "reject":
        request["status"] = "rejected"
        save_app_info(app_info)
        context.bot.send_message(
            request["user_id"], "❌ Pengajuan registrasi Anda ditolak. Hubungi admin bila diperlukan.",
            reply_markup=home_keyboard())
        query.answer("Pengajuan ditolak.")
        query.edit_message_text(f"Registrasi #{request_id}: ditolak.",
                                reply_markup=back_keyboard("admin:registrations", "⬅️ Antrian"))
        return
    users = load_user_data()
    # Eligibility is checked again now: another account may have used the number meanwhile.
    reason = trial_block_reason(request["user_id"], request.get("nohp"), app_info, users)
    mode = get_trial_mode()
    wants_trial = decision == "trial" or (decision == "approve" and mode == "auto")
    trial = get_trial_balance() if wants_trial and not reason else 0
    if str(request["user_id"]) in users:
        request["status"] = "duplicate"
        trial = 0
    else:
        users[str(request["user_id"])] = {
            "user_id": request["user_id"], "username_telegram": request.get("username_telegram"),
            "nohp": request.get("nohp"), "phone_verified": bool(request.get("phone_verified")),
            "saldo": trial, "created_at": get_current_time(),
            "servers": [], "aktif": True, "monitoring": {}, "monitoring_state": {},
            "account_type": "client",
        }
        save_user_data(users)
        # Trial is audit-only credit, never revenue; reports explicitly exclude it.
        if trial:
            add_transaction(request["user_id"], trial, "trial_balance", {"trial_balance": trial})
            _remember_trial(app_info, request["user_id"], request.get("nohp"), trial)
        request["status"] = "approved"
        request["trial_granted"] = bool(trial)
    save_app_info(app_info)
    context.bot.send_message(
        request["user_id"],
        "✅ Registrasi disetujui. " + (f"Anda menerima saldo trial Rp{trial:,}. " if trial else "") + "Ketik /menu untuk mulai.",
        reply_markup=home_keyboard())
    query.answer("Registrasi disetujui.")
    note = "dengan trial" if trial else ("tanpa trial" + (f" — {reason}" if wants_trial and reason else ""))
    query.edit_message_text(f"Registrasi #{request_id}: disetujui ({note}).",
                            reply_markup=back_keyboard("admin:registrations", "⬅️ Antrian"))


def pending_registrations_menu(query):
    """Daftar antrian registrasi untuk staf."""
    app_info = load_app_info()
    pending = [(request_id, item) for request_id, item in app_info.get("registration_requests", {}).items()
               if item.get("status") == "pending"]
    if not pending:
        query.answer("Tidak ada antrian registrasi.")
        query.edit_message_text("✅ Tidak ada pengajuan registrasi yang menunggu.", reply_markup=home_keyboard())
        return
    keyboard = []
    for request_id, item in pending[:25]:
        name = item.get("username_telegram") or item["user_id"]
        flag = "" if not trial_block_reason(item["user_id"], item.get("nohp")) else " ⚠️"
        keyboard.append([InlineKeyboardButton(f"#{request_id} · {name}{flag}", callback_data=f"reg:view:{request_id}")])
    keyboard.append([InlineKeyboardButton("🏠 Dashboard", callback_data="nav:home")])
    query.answer()
    query.edit_message_text(f"📥 Antrian registrasi ({len(pending)} menunggu):", reply_markup=InlineKeyboardMarkup(keyboard))


def registration_queue_callback(query, context):
    """Detail satu pengajuan registrasi + tombol keputusan."""
    if not is_staff(query.from_user.id):
        query.answer("Akses ditolak.", show_alert=True)
        return
    _, action, request_id = query.data.split(":", 2)
    if action != "view":
        return
    request = load_app_info().get("registration_requests", {}).get(request_id)
    if not request or request.get("status") != "pending":
        query.answer("Pengajuan sudah diproses.", show_alert=True)
        return
    query.answer()
    query.edit_message_text(_request_text(request_id, request),
                            reply_markup=_approval_keyboard(request_id, request, with_back=True))


def _notify_staff_registration(context, request_id, request):
    """Kirim pengajuan registrasi baru ke semua staf."""
    for staff_id in staff_ids():
        try:
            context.bot.send_message(staff_id, _request_text(request_id, request),
                                     reply_markup=_approval_keyboard(request_id, request))
        except Exception:
            continue
