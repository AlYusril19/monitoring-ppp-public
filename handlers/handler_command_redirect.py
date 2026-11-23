"""Text commands that open the same button menus (one implementation per feature).

Older releases had separate command logic (/addserver with arguments,
/connect conversation, /daftar, /topup). These commands now open the button
flow, so rules such as the server limit and password deletion apply equally.
"""
from configs.app_settings import is_staff
from configs.data_json_user import load_user_data
from configs.navigation import QueryFromMessage, clear_pending_inputs, home_keyboard


def _registered(update):
    """True bila user terdaftar; bila tidak, kirim petunjuk registrasi."""
    if str(update.effective_user.id) in load_user_data():
        return True
    update.effective_message.reply_text(
        "Anda belum terdaftar. Ketik /start untuk mengajukan registrasi.", reply_markup=home_keyboard())
    return False


def servers_command(update, context):
    """/listserver, /connect, /editserver, /delserver → Server Saya (pilih, ⚙️ Kelola)."""
    if not _registered(update):
        return
    from handlers.handler_menu import _show_servers
    _show_servers(QueryFromMessage(update))


def add_server_command(update, context):
    """/addserver → wizard Tambah server (password dihapus, batas server dicek)."""
    if not _registered(update):
        return
    if context.args:
        update.effective_message.reply_text(
            "Data server kini diisi lewat form agar password langsung dihapus dari chat.")
    from handlers.handler_server import start_server_wizard
    start_server_wizard(QueryFromMessage(update), context)


def daftar_command(update, context):
    """/daftar → staf: antrian registrasi; calon user: tombol registrasi."""
    if is_staff(update.effective_user.id):
        from handlers.handler_onboarding import pending_registrations_menu
        pending_registrations_menu(QueryFromMessage(update))
        return
    from handlers.handler_menu import show_menu
    show_menu(update, context)


def topup_command(update, context):
    """/topup → staf: tambah saldo manual; user: menu Saldo (QRIS + bukti)."""
    if is_staff(update.effective_user.id):
        from handlers.handler_wallet import begin_manual_topup
        begin_manual_topup(QueryFromMessage(update), context)
        return
    if not _registered(update):
        return
    from handlers.handler_wallet import wallet_menu
    wallet_menu(update, context)


def cancel_command(update, context):
    """/cancel: close any open form (registration, server, topup, admin input...)."""
    if context.user_data.get("onboarding_step"):
        from handlers.handler_onboarding import remove_reply_keyboard
        remove_reply_keyboard(context.bot, update.effective_chat.id)
    cancelled = clear_pending_inputs(context)
    update.effective_message.reply_text(
        "✖️ Input dibatalkan." if cancelled else "Tidak ada input yang sedang berjalan.",
        reply_markup=home_keyboard())
