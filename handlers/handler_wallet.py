"""Wallet request and staff approval flow, including photo proof metadata."""
from uuid import uuid4

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from configs.add_transaction import add_transaction
from configs.app_settings import (MAX_TOPUP_PACKAGES, add_topup_package, delete_topup_package,
                                  get_custom_topup_range, get_qris_file_id, get_topup_amounts,
                                  get_topup_package, get_topup_packages, is_staff, is_superadmin,
                                  package_qris, set_qris_file_id, staff_ids, update_topup_package)
from configs.data_json_user import (get_registered_username, load_app_info, load_user_data, save_app_info,
                                    save_user_data)
from configs.send_message import bot_log, chat_log
from configs.format_rupiah import format_rupiah
from configs.chat_tracker import mark_input_consumed
from configs.get_current_time import get_current_time
from configs.navigation import back_keyboard, cancel_keyboard, home_keyboard


def user_label(user_id):
    """'Nama (ID 123)' using the name recorded at registration."""
    return f"{get_registered_username(user_id)} (ID {user_id})"


def wallet_menu(update, context):
    """Menu 💳 Saldo: saldo, paket nominal (QRIS statik), nominal bebas, riwayat."""
    keyboard = [[InlineKeyboardButton(f"Rp{amount:,}", callback_data=f"wallet:amount:{amount}")]
                for amount in get_topup_amounts()]
    minimum, maximum = get_custom_topup_range()
    if get_qris_file_id():
        keyboard.append([InlineKeyboardButton("✍️ Nominal Lain", callback_data="wallet:custom")])
    keyboard.append([InlineKeyboardButton("📜 Riwayat Bulanan", callback_data="hist:monthly"),
                     InlineKeyboardButton("📜 Riwayat Tahunan", callback_data="hist:yearly")])
    keyboard.append([InlineKeyboardButton("🏠 Dashboard", callback_data="nav:home")])
    record = load_user_data().get(str(update.effective_user.id), {})
    balance = int(record.get("saldo", 0))
    text = f"💳 *Saldo Anda: Rp{balance:,}*\n\nPilih nominal topup. QRIS ditampilkan setelah nominal dipilih."
    if get_qris_file_id():
        text += f"\n✍️ *Nominal Lain*: ketik sendiri Rp{minimum:,}–Rp{maximum:,}."
    update.effective_message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


def _send_qris(context, chat_id, qris_file_id, amount, query=None):
    """Tampilkan QRIS + instruksi bayar, lalu tunggu foto bukti transfer."""
    text = (f"Nominal: *Rp{amount:,}*.\nScan QRIS, bayar *tepat Rp{amount:,}*, lalu kirim *foto bukti transfer* "
            "di chat ini.\nKetik /cancel untuk membatalkan.")
    if qris_file_id:
        # QRIS + instructions in one message, so it stays visible while paying.
        context.bot.send_photo(chat_id=chat_id, photo=qris_file_id, caption=text,
                               parse_mode="Markdown", reply_markup=cancel_keyboard())
        return
    text += "\n\n_QRIS belum diatur admin; hubungi admin untuk info pembayaran._"
    if query is not None:
        query.edit_message_text(text, parse_mode="Markdown", reply_markup=cancel_keyboard())
    else:
        context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown", reply_markup=cancel_keyboard())


def wallet_callback(query, context):
    """Tombol wallet:amount:N (paket) dan wallet:custom (nominal bebas)."""
    parts = query.data.split(":")
    if parts == ["wallet", "custom"]:
        if not get_qris_file_id():
            query.answer("Nominal bebas belum tersedia.", show_alert=True)
            return
        minimum, maximum = get_custom_topup_range()
        context.user_data.pop("pending_topup_amount", None)
        context.user_data["topup_custom_input"] = True
        query.answer()
        query.edit_message_text(f"✍️ Ketik nominal topup (angka, Rp{minimum:,}–Rp{maximum:,}).\nContoh: `{minimum}`",
                                parse_mode="Markdown", reply_markup=cancel_keyboard())
        return
    if len(parts) != 3 or parts[1] != "amount" or not parts[2].isdigit():
        return
    amount = int(parts[2])
    if get_topup_package(amount) is None:
        query.answer("Nominal sudah tidak tersedia. Buka menu Saldo lagi.", show_alert=True)
        return
    context.user_data.pop("topup_custom_input", None)
    context.user_data["pending_topup_amount"] = amount
    context.user_data["pending_topup_source"] = "package"
    query.answer()
    _send_qris(context, query.message.chat_id, package_qris(amount), amount, query)


def handle_topup_custom_input(update, context):
    """Form ✍️ Nominal Lain: validasi nominal lalu tampilkan QRIS umum. True bila dipakai."""
    if not context.user_data.get("topup_custom_input"):
        return False
    minimum, maximum = get_custom_topup_range()
    text = update.effective_message.text.strip().replace(".", "").replace(",", "")
    if not text.isdigit() or not minimum <= int(text) <= maximum:
        update.effective_message.reply_text(
            f"Nominal harus angka Rp{minimum:,}–Rp{maximum:,}. Masukkan ulang atau /cancel.",
            reply_markup=cancel_keyboard())
        return True
    amount = int(text)
    context.user_data.pop("topup_custom_input", None)
    context.user_data["pending_topup_amount"] = amount
    context.user_data["pending_topup_source"] = "custom"
    _send_qris(context, update.effective_message.chat_id, get_qris_file_id(), amount)
    return True


def _save_uploaded_qris(target, file_id):
    """Simpan foto QRIS dari superadmin sesuai target upload. Mengembalikan (teks, keyboard)."""
    back = back_keyboard("admin:pkg", "⬅️ Paket Saldo")
    if target.startswith("new:"):
        amount = int(target.split(":", 1)[1])
        add_topup_package(amount, file_id)
        return f"✅ Paket Rp{amount:,} ditambahkan dengan QRIS-nya.", back
    if target.startswith("pkg:"):
        amount = int(target.split(":", 1)[1])
        update_topup_package(amount, qris_file_id=file_id)
        return f"✅ QRIS paket Rp{amount:,} diganti.", back
    set_qris_file_id(file_id)
    return "✅ QRIS nominal bebas disimpan (juga dipakai paket yang belum punya QRIS).", back


def capture_payment_proof(update, context):
    """Foto masuk: QRIS baru (superadmin) atau bukti transfer → antrian topup."""
    target = context.user_data.pop("qris_upload", None)
    if target:
        if not is_superadmin(update.effective_user.id):
            return
        mark_input_consumed()
        target = "manual" if target is True else str(target)
        try:
            text, keyboard = _save_uploaded_qris(target, update.effective_message.photo[-1].file_id)
        except ValueError as exc:
            text, keyboard = f"❌ {exc}", back_keyboard("admin:pkg", "⬅️ Paket Saldo")
        update.effective_message.reply_text(text, reply_markup=keyboard)
        return
    amount = context.user_data.get("pending_topup_amount")
    if not amount:
        return
    user_id = update.effective_user.id
    users = load_user_data()
    if str(user_id) not in users:
        update.effective_message.reply_text("Anda belum terdaftar.", reply_markup=home_keyboard())
        context.user_data.pop("pending_topup_amount", None)
        return

    mark_input_consumed()
    request_id = uuid4().hex[:10]
    source = context.user_data.pop("pending_topup_source", "package")
    app_info = load_app_info()
    requests = app_info.setdefault("topup_requests", {})
    requests[request_id] = {
        "user_id": user_id,
        "amount": amount,
        "source": source,
        "proof_file_id": update.effective_message.photo[-1].file_id,
        "requested_at": get_current_time(),
        "status": "pending",
    }
    save_app_info(app_info)
    context.user_data.pop("pending_topup_amount", None)
    update.effective_message.reply_text(
        f"✅ Permintaan #{request_id} tercatat dan menunggu persetujuan admin.", reply_markup=home_keyboard())

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Setujui", callback_data=f"topup:approve:{request_id}"),
        InlineKeyboardButton("❌ Tolak", callback_data=f"topup:reject:{request_id}"),
    ]])
    kind = "nominal bebas" if source == "custom" else "paket"
    for staff_id in staff_ids():
        try:
            context.bot.send_photo(
                chat_id=staff_id, photo=update.effective_message.photo[-1].file_id,
                caption=(f"Permintaan saldo #{request_id}\nUser: {user_label(user_id)}\n"
                         f"Nominal: Rp{amount:,} ({kind})"), reply_markup=keyboard)
        except Exception:
            # A staff account may not have opened the bot yet; approval remains
            # available through the request id rather than losing the request.
            continue


# ---------------------------------------------------------------- admin: packages & QRIS
def packages_menu(query):
    """Menu admin 💳 Paket Saldo & QRIS: daftar paket, tambah, QRIS nominal bebas."""
    packages = get_topup_packages()
    minimum, maximum = get_custom_topup_range()
    lines = [f"• Rp{item['amount']:,} — {'✅ QRIS' if item['qris_file_id'] else '⚠️ QRIS umum'}"
             for item in packages] or ["(belum ada paket)"]
    text = ("💳 *Paket Saldo & QRIS*\n" + "\n".join(lines) +
            f"\n\nQRIS nominal bebas: {'✅ terpasang' if get_qris_file_id() else '❌ belum'}"
            f"\nBatas nominal bebas: Rp{minimum:,}–Rp{maximum:,}"
            "\n\n_Paket tanpa QRIS sendiri memakai QRIS nominal bebas._")
    keyboard = [[InlineKeyboardButton(f"Rp{item['amount']:,}", callback_data=f"admin:pkg:view:{item['amount']}")]
                for item in packages]
    superadmin = is_superadmin(query.from_user.id)
    if superadmin:
        if len(packages) < MAX_TOPUP_PACKAGES:
            keyboard.append([InlineKeyboardButton("➕ Tambah Paket", callback_data="admin:set:pkg_new")])
        keyboard.append([InlineKeyboardButton("🖼 QRIS Nominal Bebas", callback_data="admin:qris"),
                         InlineKeyboardButton("↔️ Batas Nominal", callback_data="admin:set:custom_range")])
    if get_qris_file_id():
        keyboard.append([InlineKeyboardButton("👁 Lihat QRIS Nominal Bebas", callback_data="admin:pkg:show:0")])
    keyboard.append([InlineKeyboardButton("🏠 Dashboard", callback_data="nav:home")])
    query.answer()
    query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


def package_callback(query, context, action):
    """Tombol admin:pkg:<view|show|qris|delask|del>:<nominal>."""
    parts = action.split(":")
    if len(parts) != 3 or not parts[2].isdigit():
        packages_menu(query)
        return
    step, amount = parts[1], int(parts[2])
    if step == "show":
        file_id = get_qris_file_id() if amount == 0 else (get_topup_package(amount) or {}).get("qris_file_id")
        if not file_id:
            query.answer("QRIS belum diatur.", show_alert=True)
            return
        query.answer()
        label = "nominal bebas" if amount == 0 else f"paket Rp{amount:,}"
        context.bot.send_photo(chat_id=query.message.chat_id, photo=file_id, caption=f"QRIS {label}",
                               reply_markup=back_keyboard("admin:pkg", "⬅️ Paket Saldo"))
        return
    package = get_topup_package(amount)
    if package is None:
        query.answer("Paket tidak ditemukan.", show_alert=True)
        return
    superadmin = is_superadmin(query.from_user.id)
    if step in {"qris", "delask", "del"} and not superadmin:
        query.answer("Hanya superadmin.", show_alert=True)
        return
    if step == "qris":
        context.user_data["qris_upload"] = f"pkg:{amount}"
        query.answer()
        query.edit_message_text(f"Kirim foto QRIS statik untuk paket *Rp{amount:,}*.", parse_mode="Markdown",
                                reply_markup=cancel_keyboard())
        return
    if step == "delask":
        query.answer()
        query.edit_message_text(f"Hapus paket *Rp{amount:,}* beserta QRIS-nya?", parse_mode="Markdown",
                                reply_markup=InlineKeyboardMarkup([[
                                    InlineKeyboardButton("Ya, hapus", callback_data=f"admin:pkg:del:{amount}"),
                                    InlineKeyboardButton("Batal", callback_data=f"admin:pkg:view:{amount}")]]))
        return
    if step == "del":
        delete_topup_package(amount)
        query.answer("Paket dihapus.")
        query.edit_message_text(f"✅ Paket Rp{amount:,} dihapus.", reply_markup=back_keyboard("admin:pkg", "⬅️ Paket Saldo"))
        return
    # view
    rows = []
    if package["qris_file_id"]:
        rows.append([InlineKeyboardButton("👁 Lihat QRIS", callback_data=f"admin:pkg:show:{amount}")])
    if superadmin:
        rows.append([InlineKeyboardButton("🖼 Ganti QRIS", callback_data=f"admin:pkg:qris:{amount}"),
                     InlineKeyboardButton("✏️ Ubah Nominal", callback_data=f"admin:set:pkg_edit:{amount}")])
        rows.append([InlineKeyboardButton("🗑 Hapus Paket", callback_data=f"admin:pkg:delask:{amount}")])
    rows.append([InlineKeyboardButton("⬅️ Paket Saldo", callback_data="admin:pkg"),
                 InlineKeyboardButton("🏠 Dashboard", callback_data="nav:home")])
    query.answer()
    qris = "✅ QRIS sendiri" if package["qris_file_id"] else "⚠️ memakai QRIS nominal bebas"
    query.edit_message_text(f"💳 Paket *Rp{amount:,}*\n{qris}", parse_mode="Markdown",
                            reply_markup=InlineKeyboardMarkup(rows))


def begin_qris_upload(query, context):
    """Tombol 🖼 QRIS Nominal Bebas (superadmin): foto berikutnya menjadi QRIS umum."""
    if not is_superadmin(query.from_user.id):
        query.answer("Hanya superadmin.", show_alert=True)
        return
    context.user_data["qris_upload"] = "manual"
    query.answer()
    query.edit_message_text("Kirim foto QRIS statik *tanpa nominal* untuk topup nominal bebas.",
                            parse_mode="Markdown", reply_markup=cancel_keyboard())


def topup_approval_callback(query, context):
    """Tombol topup:approve/reject: tambah saldo user atau tolak."""
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
    request["processed_at"] = get_current_time()
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
    status = "✅ disetujui" if request["status"] == "approved" else "❌ ditolak"
    result = (f"Permintaan #{request_id} {status}\n👤 {user_label(request['user_id'])}\n"
              f"💰 Rp{int(request['amount']):,}")
    if query.message.photo:
        query.edit_message_caption(caption=result, reply_markup=back_keyboard("admin:topups", "⬅️ Antrian"))
    else:
        query.edit_message_text(result, reply_markup=back_keyboard("admin:topups", "⬅️ Antrian"))


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
            f"#{request_id} · {get_registered_username(item['user_id'])} · Rp{int(item['amount']):,}",
            callback_data=f"topup:view:{request_id}")])
    keyboard.append([InlineKeyboardButton("🏠 Dashboard", callback_data="nav:home")])
    query.answer()
    query.edit_message_text(f"⏳ Antrian topup ({len(pending)} menunggu):", reply_markup=InlineKeyboardMarkup(keyboard))


def topup_queue_callback(query, context):
    """Detail satu permintaan topup di antrian."""
    if not is_staff(query.from_user.id):
        query.answer("Akses ditolak.", show_alert=True)
        return
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
        f"Permintaan topup #{request_id}\nUser: {user_label(request['user_id'])}\nNominal: Rp{int(request['amount']):,}\n"
        f"Diajukan: {request.get('requested_at', '-')}", reply_markup=keyboard)


def begin_manual_topup(query, context):
    """Mulai form ➕ Tambah Saldo manual (staf)."""
    context.user_data["manual_topup_step"] = "user_id"
    query.answer()
    query.edit_message_text(
        "Masukkan Telegram User ID penerima saldo.",
        reply_markup=cancel_keyboard())


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
            update.effective_message.reply_text("User ID tidak ditemukan. Masukkan ulang atau /cancel.",
                                                reply_markup=cancel_keyboard())
            return True
        context.user_data["manual_topup_user_id"] = value
        context.user_data["manual_topup_step"] = "amount"
        record = users[value]
        update.effective_message.reply_text(
            f"👤 {user_label(value)}\nSaldo saat ini: {format_rupiah(record.get('saldo', 0))}\n\n"
            "Masukkan nominal saldo yang akan ditambahkan.", reply_markup=cancel_keyboard())
        return True
    try:
        amount = int(value)
        if amount <= 0:
            raise ValueError
    except ValueError:
        update.effective_message.reply_text("Nominal harus berupa angka lebih dari nol. Masukkan ulang atau /cancel.",
                                            reply_markup=cancel_keyboard())
        return True
    user_id = context.user_data.pop("manual_topup_user_id")
    context.user_data.pop("manual_topup_step", None)
    users = load_user_data()
    record = users.get(user_id)
    if not record:
        update.effective_message.reply_text("User sudah tidak ditemukan.", reply_markup=home_keyboard())
        return True
    record["saldo"] = int(record.get("saldo", 0)) + amount
    save_user_data(users)
    add_transaction(int(user_id), amount, "manual_topup", {"credited_by": update.effective_user.id})
    context.bot.send_message(
        int(user_id),
        f"✅ Saldo Anda ditambahkan admin sebesar {format_rupiah(amount)}.\nSaldo sekarang: {format_rupiah(record['saldo'])}.",
        reply_markup=home_keyboard())
    admin_name = get_registered_username(update.effective_user.id)
    if admin_name == str(update.effective_user.id):
        admin_name = update.effective_user.username or update.effective_user.full_name or admin_name
    summary = (f"✅ Saldo manual berhasil ditambahkan\n"
               f"👤 Nama: {get_registered_username(user_id)}\n"
               f"🆔 ID: {user_id}\n"
               f"💰 Nominal: {format_rupiah(amount)}\n"
               f"💳 Saldo kini: {format_rupiah(record['saldo'])}\n"
               f"🛡 Oleh: {admin_name}")
    update.effective_message.reply_text(summary, reply_markup=back_keyboard("admin:manualtopup", "➕ Tambah lagi"))
    try:  # audit trail in the admin log chat
        bot_log.send_message(chat_id=chat_log, text=summary)
    except Exception as exc:
        print(f"Gagal kirim log saldo manual: {exc}")
    return True


def set_qris_command(update, context):
    """/setqris: superadmin mengirim foto QRIS berikutnya."""
    if not is_superadmin(update.effective_user.id):
        update.effective_message.reply_text("Hanya superadmin yang dapat mengganti QRIS.", reply_markup=home_keyboard())
        return
    context.user_data["qris_upload"] = "manual"
    update.effective_message.reply_text(
        "Kirim foto QRIS statik tanpa nominal sekarang. Foto berikutnya dipakai untuk topup nominal bebas "
        "(QRIS per paket diatur di Dashboard Admin → 💳 Paket Saldo & QRIS).", reply_markup=cancel_keyboard())
