"""Access control in one place: which buttons/commands are staff-only.

Telegram clients can send any callback_data (modified clients, replayed
buttons), so every staff-only prefix is checked centrally in
handler_menu.menu_callback, and staff-only commands are wrapped with
staff_only() in main.py. Handlers keep their own checks as a second layer.
"""
import time
from functools import wraps

from configs.app_settings import is_staff
from configs.data_json_user import load_user_data

# callback_data prefixes that only staff may press.
STAFF_CALLBACK_PREFIXES = ("admin:", "users:", "reg:", "topup:", "refund:")

# Buttons an unregistered (non-staff) Telegram account may press.
GUEST_CALLBACKS = ("nav:home", "onboard:register", "input:cancel")

# Do not flood the admin log: one report per user per this many seconds.
_REPORT_INTERVAL = 600
_last_report = {}


def is_registered(user_id):
    """True bila user punya record di datauser.json."""
    return str(user_id) in load_user_data()


def report_denied(user, what):
    """Catat percobaan akses fitur admin oleh non-staf ke chat log (dibatasi per user)."""
    user_id = getattr(user, "id", user)
    now = time.time()
    if now - _last_report.get(user_id, 0) < _REPORT_INTERVAL:
        return
    _last_report[user_id] = now
    name = getattr(user, "username", None) or getattr(user, "full_name", None) or "-"
    print(f"Akses admin ditolak: {user_id} ({name}) -> {what}")
    try:
        from configs.send_message import bot_log, chat_log
        bot_log.send_message(chat_id=chat_log, text=f"🚫 Akses admin ditolak\nUser: {name} (ID {user_id})\nAksi: {what}")
    except Exception as exc:
        print(f"Gagal kirim log akses ditolak: {exc}")


def callback_allowed(query):
    """Cek tombol sebelum diproses. Mengembalikan False (dan menjawab query) bila ditolak."""
    data = query.data or ""
    user_id = query.from_user.id
    if is_staff(user_id):
        return True
    if data.startswith(STAFF_CALLBACK_PREFIXES):
        report_denied(query.from_user, f"tombol {data[:40]}")
        query.answer("Akses ditolak.", show_alert=True)
        return False
    if data not in GUEST_CALLBACKS and not is_registered(user_id):
        query.answer("Anda belum terdaftar. Ketik /start untuk registrasi.", show_alert=True)
        return False
    return True


def staff_only(handler):
    """Bungkus command khusus staf: non-staf mendapat penolakan singkat dan dicatat."""
    @wraps(handler)
    def wrapper(update, context, *args, **kwargs):
        user = update.effective_user
        if not is_staff(user.id):
            report_denied(user, f"command {getattr(update.effective_message, 'text', '')[:40]}")
            from configs.navigation import home_keyboard
            update.effective_message.reply_text("❌ Perintah ini tidak tersedia untuk akun Anda.",
                                                reply_markup=home_keyboard())
            return None
        return handler(update, context, *args, **kwargs)
    return wrapper
