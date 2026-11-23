from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from configs.chat_tracker import in_background, keep_messages
from configs.get_current_time import get_current_time
from configs.send_message import send_message, send_down_report, chat_log, bot_log, escape_md
from configs.mikrotik_function import (RouterError, connect_router, get_down_users, get_name_server,
                                       router_error_text, validate_address)
from models.userdata import UserData, user_data_dict
from configs.data_json_user import load_user_data, get_registered_username
from configs.format_rupiah import format_rupiah
from configs.billing import charge_user
from configs.app_settings import ALERT_LABELS, alert_level, get_monitoring_config, is_staff
from configs.navigation import dashboard_row, home_keyboard, session_action_keyboard, topup_keyboard, wizard_keyboard

def start_command_handler(update, context):
    """/testppp: cek PPPoE pada sesi router aktif."""
    user_id = update.effective_user.id
    saldo_user = load_user_data()

    # Pengecekan Saldo
    if str(user_id) not in saldo_user and not is_staff(user_id):
        update.effective_message.reply_text("Anda belum terdaftar, silahkan /start untuk registrasi.",
                                            reply_markup=home_keyboard())
        return

    user_data = user_data_dict.get(user_id)

    if user_data is None:
        update.effective_message.reply_text(
            "Anda belum terhubung ke server. Pilih server lewat /connect (Server Saya) atau /custom.",
            reply_markup=home_keyboard())
    else:
        # Jika semua data ada, lanjutkan dengan proses normal
        in_background(run_pppoe_test, context, user_id, update.effective_chat.id, user_data)
        
def start_command_handler_by_custom(update, context):
    """/custom: mulai form Server Custom."""
    return begin_custom_server(context, update.effective_user.id, update.effective_message)


def begin_custom_server(context, user_id, message):
    """Start a temporary server session; it is never written to datauser.json."""
    context.user_data["custom_server_wizard"] = {"step": "ip"}
    message.reply_text(
        "🔧 *Server Custom*\nMasukkan IP atau hostname/DDNS MikroTik (port API lain: `host:port`). Data ini hanya dipakai untuk sesi saat ini dan tidak disimpan.",
        parse_mode="Markdown", reply_markup=wizard_keyboard("custom"))


def handle_custom_server_input(update, context):
    """Consume temporary server credentials and delete the password message."""
    wizard = context.user_data.get("custom_server_wizard")
    if not wizard:
        return False
    value = update.effective_message.text.strip()
    step = wizard["step"]
    if step == "ip":
        problem = validate_address(value)
        if problem:
            update.effective_message.reply_text(f"{problem}\nMasukkan ulang:", parse_mode="Markdown",
                                                reply_markup=wizard_keyboard("custom"))
            return True
        wizard["ip"] = value
        wizard["step"] = "username"
        update.effective_message.reply_text("Masukkan username RouterOS (gunakan akun READ):", reply_markup=wizard_keyboard("custom"))
        return True
    if step == "username":
        wizard["username"] = value
        wizard["step"] = "password"
        update.effective_message.reply_text("Masukkan password. Pesan password akan dihapus setelah diterima:", reply_markup=wizard_keyboard("custom"))
        return True
    if step == "password":
        try:
            update.effective_message.delete()
        except Exception:
            pass
        context.user_data.pop("custom_server_wizard", None)
        waiting = update.effective_chat.send_message("⏳ Menguji koneksi ke router...")
        in_background(_test_custom_server, update, context, wizard, value, waiting)  # never blocks other users
        return True
    return False


def _test_custom_server(update, context, wizard, password, waiting):
    """Uji koneksi Server Custom; berhasil → jadikan sesi aktif."""
    try:
        connection = connect_router(wizard["ip"], wizard["username"], password)
        identity = get_name_server(connection)
    except RouterError as exc:
        _delete_quietly(context.bot, waiting)
        update.effective_chat.send_message(
            f"{router_error_text(exc, wizard['ip'], wizard['ip'])}\n\nServer custom belum tersambung dan saldo tidak dipotong. "
            "Password sudah dihapus dari chat.",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔁 Isi Ulang", callback_data="input:reset:custom")], dashboard_row()]))
        return
    _delete_quietly(context.bot, waiting)
    session = user_data_dict.setdefault(update.effective_user.id, UserData())
    session.ip_address = wizard["ip"]
    session.router_username = wizard["username"]
    session.router_password = password
    session.server_name = None  # temporary server, not in Server Saya
    session.interface = None
    session.www_port = None
    update.effective_chat.send_message(
        f"✅ Server custom *{escape_md(identity or wizard['ip'])}* tersambung untuk sesi ini. "
        "Password telah dihapus dari chat. Pilih aksi berikutnya:",
        parse_mode="Markdown", reply_markup=session_action_keyboard())


def run_pppoe_test(context, user_id, chat_id, user_data):
    """Run the PPPoE test from either a command or an inline callback.

    The balance is charged only after the router answered; any connection
    problem gets a friendly message and costs nothing.
    """
    # Logs must use the registration record, not a mutable Telegram username.
    username_telegram = escape_md(get_registered_username(user_id))
    bot = context.bot
    label = getattr(user_data, "server_name", None) or user_data.ip_address
    waiting = send_message(bot, chat_id, "⏳ Memeriksa router...")

    try:
        connection = connect_router(user_data.ip_address, user_data.router_username, user_data.router_password)
        nama_server = escape_md(get_name_server(connection) or label)
        config = get_monitoring_config(load_user_data().get(str(user_id), {}))
        down_users = get_down_users(connection, config.get("excluded_profiles"))
    except RouterError as exc:
        print(f"Cek PPPoE {user_id}/{label} gagal: {exc.detail or exc.kind}")
        _delete_quietly(bot, waiting)
        if exc.kind == "login":
            # Wrong credentials: drop the session so the user re-selects or re-enters the server.
            user_data.ip_address = user_data.router_username = user_data.router_password = None
            user_data.interface = None
            keyboard = home_keyboard()
            hint = "Perbaiki data server lewat ⚙️ Kelola → ✏️ Edit Server, lalu coba lagi."
        else:
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Cek Lagi", callback_data="menu:pppoe")],
                                             dashboard_row()])
            hint = "Harap cek kondisi router/jaringan di lokasi, lalu coba lagi."
        send_message(bot, chat_id, f"{router_error_text(exc, label, user_data.ip_address)}\n{hint}\n\n💰 Saldo tidak dipotong.",
                     reply_markup=keyboard)
        return

    success, start_cost, remaining = charge_user(user_id, "testppp")
    if not success:
        _delete_quietly(bot, waiting)
        send_message(bot, chat_id, "Mohon maaf saldo anda tidak mencukupi, silahkan melakukan topup saldo",
                     reply_markup=topup_keyboard())
        return

    level = alert_level(len(down_users), config)
    # One log message per check; it stays in the chat (not auto-deleted).
    header = f"📡 *Cek PPPoE* · *{nama_server}*\n🕒 {get_current_time()}"
    footer = "\n".join(part for part in (ALERT_LABELS.get(level, ""), f"Biaya: Rp{start_cost}") if part)
    with keep_messages():
        if down_users:
            # Every down customer is listed; a long list becomes a .txt attachment.
            send_down_report(bot, chat_id, header, down_users, footer)
        else:
            send_message(bot, chat_id, f"{header}\n\nUser Status UP Semua 🤩\n\n{footer}")
    send_message(bot_log, chat_log, f"user *{username_telegram}* login ke *{nama_server}*\n"
                                    f"User Down *({len(down_users)} Users)*\n"
                                    f"{ALERT_LABELS.get(level, '')}\n"
                                    f"Sisa saldo User {format_rupiah(remaining or 0)}")
    _delete_quietly(bot, waiting)
    bot.send_message(chat_id=chat_id, text="Pilih aksi berikutnya:", reply_markup=session_action_keyboard())


def _delete_quietly(bot, message):
    """Hapus pesan tanpa error (untuk pesan ⏳)."""
    try:
        bot.delete_message(chat_id=message.chat_id, message_id=message.message_id)
    except Exception:
        pass
