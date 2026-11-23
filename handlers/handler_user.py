"""User management for staff: active/archived lists, balances, archive/activate.

Reachable from Dashboard Admin → 👥 Data User and from the matching /commands.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from configs.app_settings import get_server_limit, is_staff, is_superadmin
from configs.data_json_user import load_user_data, save_user_data
from configs.format_rupiah import format_rupiah
from configs.navigation import back_keyboard, home_keyboard
from configs.send_message import escape_md, send_message


def users_menu(query):
    """Menu 👥 Data User."""
    users = load_user_data()
    active = sum(1 for record in users.values() if record.get("aktif", True))
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 User Aktif", callback_data="users:active"),
         InlineKeyboardButton("📦 User Arsip", callback_data="users:archived")],
        [InlineKeyboardButton("💰 Saldo User", callback_data="users:balances")],
        [InlineKeyboardButton("📦 Arsipkan User", callback_data="admin:set:archive"),
         InlineKeyboardButton("✅ Aktifkan User", callback_data="admin:set:activate")],
        [InlineKeyboardButton("🎁 Trial & Registrasi", callback_data="admin:trial"),
         InlineKeyboardButton("🗑 Hapus User", callback_data="admin:set:delete_user")],
        [InlineKeyboardButton("🏠 Dashboard", callback_data="nav:home")],
    ])
    query.answer()
    query.edit_message_text(
        f"👥 *Data User*\nTerdaftar: {len(users)} · Aktif: {active} · Arsip: {len(users) - active}",
        parse_mode="Markdown", reply_markup=keyboard)


def users_callback(update, context):
    """Tombol users:* (aktif, arsip, saldo)."""
    query = update.callback_query
    if not is_staff(query.from_user.id):
        query.answer("Akses ditolak.", show_alert=True)
        return
    action = query.data.split(":", 1)[1]
    if action.startswith("delete:"):
        _delete_user(query, context, action.split(":", 1)[1])
        return
    query.answer()
    if action == "active":
        user_aktif(update, context)
    elif action == "archived":
        user_arsip(update, context)
    elif action == "balances":
        cek_semua_saldo(update, context)


def _delete_user(query, context, target_id):
    """Tombol users:delete:<id> (superadmin): hapus akun, beri tahu user beserta refund."""
    from handlers.handler_refund import delete_account, deletion_result_text
    if not is_superadmin(query.from_user.id):
        query.answer("Hanya superadmin.", show_alert=True)
        return
    result = delete_account(context.bot, target_id, deleted_by=query.from_user.id) if target_id.isdigit() else None
    if result is None:
        query.answer("User tidak ditemukan.", show_alert=True)
        return
    try:
        context.bot.send_message(int(target_id), deletion_result_text(result, by_admin=False).replace(
            "Akun Anda telah dihapus.", "Akun Anda telah dihapus oleh admin."), parse_mode="Markdown",
            reply_markup=home_keyboard("✨ Mulai lagi"))
    except Exception as exc:
        print(f"Gagal memberi tahu user {target_id} yang dihapus: {exc}")
    query.answer("User dihapus.")
    query.edit_message_text(deletion_result_text(result, by_admin=True), parse_mode="Markdown",
                            reply_markup=back_keyboard("admin:users", "⬅️ Data User"))


def set_user_active(target_id, active):
    """Archive/activate one user. Returns a message; raises ValueError if not found."""
    target_id = str(target_id).strip()
    users = load_user_data()
    if target_id not in users:
        raise ValueError(f"User {target_id} tidak ditemukan.")
    users[target_id]["aktif"] = bool(active)
    save_user_data(users)
    return f"✅ User {target_id} " + ("diaktifkan kembali." if active else "diarsipkan. Monitoring otomatis dihentikan.")


def _toggle_command(update, context, active):
    """Dasar /arsipkan dan /aktifkan."""
    chat_id = update.effective_chat.id
    if not is_staff(update.effective_user.id):
        send_message(context.bot, chat_id, "❌ Akses ditolak.", with_dashboard=True)
        return
    if not context.args:
        send_message(context.bot, chat_id, f"Gunakan: /{'aktifkan' if active else 'arsipkan'} <user\\_id>",
                     with_dashboard=True)
        return
    try:
        send_message(context.bot, chat_id, set_user_active(context.args[0], active), with_dashboard=True)
    except ValueError as exc:
        send_message(context.bot, chat_id, f"❌ {exc}", with_dashboard=True)


def arsipkan_user(update, context):
    """/arsipkan <user_id>."""
    _toggle_command(update, context, False)


def aktifkan_user(update, context):
    """/aktifkan <user_id>."""
    _toggle_command(update, context, True)


def _user_line(uid, record):
    """Satu baris ringkasan user (ID, nama, saldo, server)."""
    name = escape_md(record.get("username_telegram") or "Tidak diketahui")
    servers = len(record.get("servers", []))
    return (f"👤 `{uid}` - {name}\n"
            f"    {format_rupiah(record.get('saldo', 0))} · server {servers}/{get_server_limit(uid)}")


def _send_list(update, context, title, lines, empty):
    """Kirim daftar user ke staf (dengan tombol kembali)."""
    chat_id = update.effective_chat.id
    if not is_staff(update.effective_user.id):
        send_message(context.bot, chat_id, "❌ Akses ditolak.", with_dashboard=True)
        return
    text = f"{title}\n\n" + "\n".join(lines) if lines else empty
    context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown",
                             reply_markup=back_keyboard("admin:users", "⬅️ Data User"))


def user_aktif(update, context):
    """/useraktif dan tombol 👥 User Aktif."""
    users = load_user_data()
    lines = [_user_line(uid, r) for uid, r in users.items() if r.get("aktif", True)]
    _send_list(update, context, "📋 *Daftar User Aktif:*", lines, "Tidak ada user yang aktif.")


def user_arsip(update, context):
    """/userarsip dan tombol 📦 User Arsip."""
    users = load_user_data()
    lines = [_user_line(uid, r) + f"\n    📱 {escape_md(r.get('nohp', '-'))}"
             for uid, r in users.items() if not r.get("aktif", True)]
    _send_list(update, context, "📦 *Daftar User Arsip:*", lines, "Tidak ada user dalam arsip.")


def cek_semua_saldo(update, context):
    """/saldouser dan tombol 💰 Saldo User."""
    users = load_user_data()
    lines = [f"👤 `{uid}` - {escape_md(r.get('username_telegram') or '-')}: {format_rupiah(r.get('saldo', 0))}"
             for uid, r in users.items() if r.get("aktif", True)]
    total = sum(int(r.get("saldo", 0)) for r in users.values() if r.get("aktif", True))
    if lines:
        lines.append(f"\nTotal saldo user aktif: {format_rupiah(total)}")
    _send_list(update, context, "💰 *Saldo semua user aktif:*", lines, "Tidak ada user aktif.")
