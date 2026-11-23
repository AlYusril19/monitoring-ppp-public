"""Server Saya: add/edit wizard (buttons). /addserver etc. open the same flow.

The per-user server limit comes from configs.app_settings.get_server_limit()
(admin setting "Batas Server", default 5).
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from configs.app_settings import get_server_limit
from configs.mikrotik_function import (RouterError, connect_router, get_name_server, router_error_text,
                                       validate_address)
from configs.chat_tracker import in_background
from configs.data_json_user import DATA_LOCK, load_user_data, save_user_data
from configs.get_current_time import get_current_time
from configs.navigation import back_keyboard, home_keyboard, session_action_keyboard, wizard_keyboard
from configs.send_message import escape_md


def server_limit_reached(user_id):
    """Return (reached, used, limit) for the user's saved servers."""
    used = len(load_user_data().get(str(user_id), {}).get("servers", []))
    limit = get_server_limit(user_id)
    return used >= limit, used, limit


def _limit_text(used, limit):
    """Teks peringatan batas server."""
    return (f"⚠️ Batas server tercapai ({used}/{limit}).\n"
            "Hapus server yang tidak dipakai melalui ⚙️ Kelola, atau hubungi admin.")


def start_server_wizard(query, context):
    """Start a sequential server form from an inline button or /addserver."""
    reached, used, limit = server_limit_reached(query.from_user.id)
    if reached:
        query.answer()
        query.edit_message_text(_limit_text(used, limit), reply_markup=back_keyboard("menu:servers", "⬅️ Server Saya"))
        return
    context.user_data.pop("server_unverified", None)
    context.user_data["server_wizard"] = {"step": "name"}
    query.answer()
    query.edit_message_text(f"Server {used + 1}/{limit}. Nama server apa yang ingin disimpan?",
                            reply_markup=wizard_keyboard("stored"))


def start_edit_server_wizard(query, context, index):
    """Edit a saved server through the same safe, password-deleting wizard."""
    servers = load_user_data().get(str(query.from_user.id), {}).get("servers", [])
    if index >= len(servers):
        query.answer("Server tidak ditemukan.", show_alert=True)
        return
    server = servers[index]
    context.user_data.pop("server_unverified", None)
    context.user_data["server_wizard"] = {"mode": "edit", "index": index, "step": "name"}
    query.answer()
    query.edit_message_text(
        f"Ubah server *{escape_md(server['name'])}*. Masukkan nama server baru:",
        parse_mode="Markdown", reply_markup=wizard_keyboard("stored"))


def handle_server_wizard(update, context):
    """Consume form input. Password messages are removed immediately."""
    wizard = context.user_data.get("server_wizard")
    if not wizard:
        return False
    value = update.effective_message.text.strip()
    step = wizard["step"]
    prompts = {
        "name": ("name", "Masukkan IP atau hostname/DDNS MikroTik.\nPort API bukan 8728? Tulis dengan port, contoh `router.ddns.net:8000`."),
        "ip": ("ip", "Masukkan username RouterOS (gunakan akun READ):"),
        "username": ("username", "Masukkan password RouterOS. Pesan ini akan dihapus setelah dibaca:"),
    }
    if step == "ip":
        problem = validate_address(value)
        if problem:
            update.effective_message.reply_text(f"{problem}\nMasukkan ulang:", parse_mode="Markdown",
                                                reply_markup=wizard_keyboard("stored"))
            return True
    if step in prompts:
        field, prompt = prompts[step]
        wizard[field] = value
        wizard["step"] = {"name": "ip", "ip": "username", "username": "password"}[step]
        update.effective_message.reply_text(prompt, parse_mode="Markdown", reply_markup=wizard_keyboard("stored"))
        return True

    if step == "password":
        wizard["password"] = value
        try:
            update.effective_message.delete()
        except Exception:
            pass
        context.user_data.pop("server_wizard", None)
        waiting = update.effective_chat.send_message("⏳ Menguji koneksi ke router...")
        # The router test can take seconds: run it off the dispatcher thread.
        in_background(_test_and_store, update, context, wizard, waiting)
        return True
    return False


def _test_and_store(update, context, wizard, waiting):
    """Uji koneksi router dari form, lalu simpan (berhasil) atau tawarkan isi ulang / simpan tanpa cek."""
    try:
        identity = get_name_server(connect_router(wizard["ip"], wizard["username"], wizard["password"]))
    except RouterError as exc:
        _delete_quietly(waiting)
        # Not saved yet: the user fixes the data, or saves anyway when the router is only offline now.
        context.user_data["server_unverified"] = wizard
        rows = [[InlineKeyboardButton("🔁 Isi Ulang",
                                      callback_data=(f"srv:edit:{wizard['index']}" if wizard.get("mode") == "edit"
                                                     else "input:reset:stored"))]]
        if exc.kind != "login":
            rows.append([InlineKeyboardButton("💾 Simpan Tanpa Cek", callback_data="srv:forcesave")])
        rows.append([InlineKeyboardButton("✖️ Batal", callback_data="input:cancel")])
        update.effective_chat.send_message(
            f"{router_error_text(exc, wizard['name'], wizard['ip'])}\n\nServer *belum disimpan*. Password sudah dihapus dari chat.",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(rows))
        return
    _delete_quietly(waiting)
    text, keyboard = _store_server(update.effective_user.id, wizard)
    if keyboard is session_action_keyboard and identity:
        text += f"\n🟢 Koneksi berhasil (router: {identity})."
    update.effective_chat.send_message(text, reply_markup=keyboard())


def _delete_quietly(message):
    """Hapus pesan ⏳ tanpa error."""
    try:
        message.delete()
    except Exception:
        pass


def _store_server(user_id, wizard):
    """Save the wizard's server; return (text, keyboard factory)."""
    with DATA_LOCK:  # may run in a background task
        return _store_server_locked(user_id, wizard)


def _store_server_locked(user_id, wizard):
    """Isi _store_server (DATA_LOCK dipegang)."""
    users = load_user_data()
    record = users.get(str(user_id))
    if not record:
        return "Akun tidak ditemukan. Silakan registrasi kembali.", home_keyboard
    servers_back = lambda: back_keyboard("menu:servers", "⬅️ Server Saya")  # noqa: E731
    now = get_current_time()
    server_data = {
        "name": wizard["name"], "ip": wizard["ip"], "username": wizard["username"],
        "password": wizard["password"], "created_at": now, "updated_at": now,
    }
    servers = record.setdefault("servers", [])
    if wizard.get("mode") == "edit":
        index = wizard.get("index")
        if index is None or index >= len(servers):
            return "Server tidak ditemukan lagi. Pengubahan dibatalkan.", servers_back
        server_data["created_at"] = servers[index].get("created_at", now)
        if servers[index].get("www_port"):
            server_data["www_port"] = servers[index]["www_port"]  # editing keeps the web port
        servers[index] = server_data
        result = f"✅ Server {wizard['name']} diperbarui. Password Anda sudah dihapus dari chat."
    else:
        # Re-check: the limit may have been lowered while the form was open.
        limit = get_server_limit(user_id)
        if len(servers) >= limit:
            return _limit_text(len(servers), limit), servers_back
        servers.append(server_data)
        result = (f"✅ Server {wizard['name']} tersimpan ({len(servers)}/{limit}). "
                  "Password Anda sudah dihapus dari chat.")
    save_user_data(users)
    return result, session_action_keyboard


def force_save_server(query, context):
    """Tombol 💾 Simpan Tanpa Cek: simpan server yang gagal diuji (router sedang offline)."""
    wizard = context.user_data.pop("server_unverified", None)
    query.answer()
    if not wizard:
        query.edit_message_text("Data server sudah tidak tersedia. Silakan isi ulang.",
                                reply_markup=back_keyboard("menu:servers", "⬅️ Server Saya"))
        return
    text, keyboard = _store_server(query.from_user.id, wizard)
    if keyboard is session_action_keyboard:
        text += "\n⚠️ Koneksi belum berhasil diuji; cek PPPoE akan memberi tahu bila router masih tidak terhubung."
    query.edit_message_text(text, reply_markup=keyboard())
