"""Account deletion with a balance refund notice, and the staff refund queue.

Refund rule (admin policy, Dashboard Admin → ⚙️ Harga & Role → 💸 Refund):
  paid balance  = current balance − trial credit ever received (never below 0)
  refund amount = paid balance × refund_percent / 100   (rounded down)
Trial credit is never paid out as money, so deleting and re-registering an
account cannot turn a trial into cash. Staff accounts get no refund.

The refund is paid outside the bot (transfer); staff mark it ✅ Sudah Dibayar
in 💸 Antrian Refund and the user is told.
"""
from uuid import uuid4

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from configs.app_settings import get_refund_percent, is_staff, staff_ids
from configs.data_json_user import load_app_info, load_user_data, save_app_info, save_user_data
from configs.get_current_time import get_current_time
from configs.navigation import back_keyboard, home_keyboard
from configs.send_message import bot_log, chat_log, escape_md
from models.userdata import user_data_dict


def refund_quote(user_id):
    """Hitung refund untuk satu user; None bila user tidak terdaftar."""
    record = load_user_data().get(str(user_id))
    if record is None:
        return None
    balance = max(0, int(record.get("saldo", 0)))
    trial = sum(int(item.get("amount", 0)) for item in record.get("transactions", [])
                if item.get("type") == "trial_balance" and int(item.get("amount", 0)) > 0)
    paid = max(0, balance - trial)
    percent = get_refund_percent()
    amount = 0 if is_staff(user_id) else paid * percent // 100
    return {"user_id": int(user_id), "name": record.get("username_telegram") or str(user_id),
            "nohp": record.get("nohp") or "-", "balance": balance, "trial_part": balance - paid,
            "paid_balance": paid, "percent": percent, "amount": amount}


def deletion_notice(quote):
    """Pemberitahuan refund (Markdown) sebelum akun dihapus."""
    lines = [f"💰 Saldo saat ini: *Rp{quote['balance']:,}*"]
    if quote["trial_part"]:
        lines.append(f"🎁 Bagian saldo trial (tidak direfund): Rp{quote['trial_part']:,}")
    lines.append(f"💸 Kebijakan refund: *{quote['percent']}%* dari saldo berbayar (Rp{quote['paid_balance']:,})")
    if quote["amount"]:
        lines.append(f"➡️ Refund uang: *Rp{quote['amount']:,}*, dikirim admin ke nomor "
                     f"{escape_md(quote['nohp'])} setelah akun dihapus.")
    else:
        lines.append("➡️ Tidak ada refund uang untuk akun ini.")
    return "\n".join(lines)


def deletion_result_text(result, by_admin):
    """Pesan hasil penghapusan untuk user (by_admin=False) atau untuk admin (True)."""
    if by_admin:
        text = f"✅ User *{escape_md(result['name'])}* (ID {result['user_id']}) dihapus."
        if result.get("refund_id"):
            text += f"\n💸 Refund Rp{result['amount']:,} (#{result['refund_id']}) masuk Antrian Refund."
        else:
            text += "\nTidak ada refund uang."
        return text
    text = "🗑 *Akun Anda telah dihapus.*\n"
    if result.get("refund_id"):
        text += (f"💸 Refund *Rp{result['amount']:,}* (#{result['refund_id']}) akan dikirim admin ke nomor "
                 f"{escape_md(result['nohp'])}. Anda akan diberi tahu setelah dibayar.\n")
    else:
        text += "Tidak ada refund uang sesuai kebijakan refund.\n"
    return text + "Ketik /start bila ingin mendaftar lagi."


def delete_account(bot, user_id, deleted_by=None):
    """Hapus akun, batalkan topup yang menunggu, buat permintaan refund. None bila tidak ada."""
    quote = refund_quote(user_id)
    if quote is None:
        return None
    users = load_user_data()
    users.pop(str(user_id), None)
    save_user_data(users)
    user_data_dict.pop(int(user_id), None)

    app_info = load_app_info()
    now = get_current_time()
    for request in app_info.get("topup_requests", {}).values():
        if str(request.get("user_id")) == str(user_id) and request.get("status") == "pending":
            request.update(status="cancelled", processed_at=now, note="akun dihapus")
    result = dict(quote, refund_id=None, deleted_by=deleted_by or int(user_id), deleted_at=now)
    if quote["amount"] > 0:
        refund_id = uuid4().hex[:10]
        app_info.setdefault("refund_requests", {})[refund_id] = dict(
            quote, status="pending", requested_at=now, deleted_by=result["deleted_by"])
        result["refund_id"] = refund_id
    save_app_info(app_info)

    who = "user sendiri" if not deleted_by else f"admin {deleted_by}"
    summary = (f"🗑 Akun dihapus ({who})\n👤 {quote['name']} (ID {user_id})\n📱 {quote['nohp']}\n"
               f"💰 Saldo Rp{quote['balance']:,} · refund {quote['percent']}% = Rp{quote['amount']:,}")
    try:
        bot_log.send_message(chat_id=chat_log, text=summary)
    except Exception as exc:
        print(f"Gagal kirim log hapus akun: {exc}")
    if result["refund_id"]:
        _notify_staff(bot, result["refund_id"], quote)
    return result


def _refund_keyboard(refund_id, with_back=False):
    """Tombol keputusan refund."""
    rows = [[InlineKeyboardButton("✅ Sudah Dibayar", callback_data=f"refund:paid:{refund_id}"),
             InlineKeyboardButton("❌ Batalkan", callback_data=f"refund:cancel:{refund_id}")]]
    if with_back:
        rows.append([InlineKeyboardButton("⬅️ Antrian Refund", callback_data="admin:refunds")])
    return InlineKeyboardMarkup(rows)


def _refund_text(refund_id, item):
    """Ringkasan satu permintaan refund untuk staf."""
    return (f"💸 Refund #{refund_id}\nUser: {item.get('name')} (ID {item.get('user_id')})\n"
            f"Nomor: {item.get('nohp')}\nSaldo saat dihapus: Rp{int(item.get('balance', 0)):,} "
            f"(trial Rp{int(item.get('trial_part', 0)):,})\nKebijakan: {item.get('percent')}%\n"
            f"Refund: Rp{int(item.get('amount', 0)):,}\nDiajukan: {item.get('requested_at', '-')}")


def _notify_staff(bot, refund_id, item):
    """Kirim permintaan refund baru ke semua staf."""
    for staff_id in staff_ids():
        try:
            bot.send_message(staff_id, _refund_text(refund_id, item), reply_markup=_refund_keyboard(refund_id))
        except Exception:
            continue


def pending_refunds_menu(query):
    """Antrian refund yang belum dibayar."""
    pending = [(refund_id, item) for refund_id, item in load_app_info().get("refund_requests", {}).items()
               if item.get("status") == "pending"]
    if not pending:
        query.answer("Tidak ada antrian refund.")
        query.edit_message_text("✅ Tidak ada refund yang menunggu pembayaran.", reply_markup=home_keyboard())
        return
    keyboard = [[InlineKeyboardButton(f"#{refund_id} · {item.get('name')} · Rp{int(item.get('amount', 0)):,}",
                                      callback_data=f"refund:view:{refund_id}")] for refund_id, item in pending[:25]]
    keyboard.append([InlineKeyboardButton("🏠 Dashboard", callback_data="nav:home")])
    query.answer()
    query.edit_message_text(f"💸 Antrian refund ({len(pending)} menunggu):", reply_markup=InlineKeyboardMarkup(keyboard))


def refund_callback(query, context):
    """Tombol refund:view/paid/cancel."""
    if not is_staff(query.from_user.id):
        query.answer("Akses ditolak.", show_alert=True)
        return
    _, action, refund_id = query.data.split(":", 2)
    app_info = load_app_info()
    item = app_info.get("refund_requests", {}).get(refund_id)
    if not item or item.get("status") != "pending":
        query.answer("Refund sudah diproses.", show_alert=True)
        return
    if action == "view":
        query.answer()
        query.edit_message_text(_refund_text(refund_id, item), reply_markup=_refund_keyboard(refund_id, True))
        return
    if action not in {"paid", "cancel"}:
        return
    item.update(status="paid" if action == "paid" else "cancelled", processed_by=query.from_user.id,
                processed_at=get_current_time())
    save_app_info(app_info)
    if action == "paid":
        message = f"✅ Refund #{refund_id} sebesar Rp{int(item['amount']):,} telah dikirim admin ke nomor {item.get('nohp')}."
    else:
        message = f"❌ Refund #{refund_id} dibatalkan admin. Hubungi admin bila ada pertanyaan."
    try:
        context.bot.send_message(item["user_id"], message, reply_markup=home_keyboard())
    except Exception as exc:
        print(f"Gagal memberi tahu refund ke {item['user_id']}: {exc}")
    query.answer("Refund diproses.")
    status = "✅ sudah dibayar" if action == "paid" else "❌ dibatalkan"
    query.edit_message_text(f"Refund #{refund_id} {status}\n👤 {item.get('name')} (ID {item['user_id']})\n"
                            f"💸 Rp{int(item['amount']):,}", reply_markup=back_keyboard("admin:refunds", "⬅️ Antrian Refund"))
