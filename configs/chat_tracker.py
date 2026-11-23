"""Keep private chats short: bot replies are temporary, monitoring results are logs.

How it works
  * Every message the bot sends in a private chat is recorded (chat_messages.json).
  * While an update (button/command/form input) is being handled, messages the
    bot sends to that chat are *ephemeral*. Before the next update of that chat
    is handled, all ephemeral messages are deleted.
  * Code wraps monitoring results in ``with keep_messages():`` so they stay as a
    log (PPPoE result, traffic graph). Messages sent outside an update (scheduler
    notifications) are logs automatically.
  * A log message is never overwritten: editing it sends a new message instead.
  * The user's own command / form input is deleted after it is handled.
  * ``clear_chat`` deletes every recorded message of a chat (🗑 Bersihkan).

Speed: deleting old messages never delays a reply. The registry is updated at
once and the Telegram delete calls run on a small background pool. Slow work
(router checks) runs through ``in_background`` so one slow router never blocks
other users; it keeps this chat's tracking (temporary replies stay temporary).

Telegram only allows deleting messages younger than 48 hours.
"""
import json
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

from configs.data_json_user import BASE_DIR, write_json_atomic

STORE_FILE = os.path.join(BASE_DIR, "chat_messages.json")
MAX_AGE_SECONDS = 47 * 3600  # Telegram limit is 48 h

_lock = threading.Lock()
_local = threading.local()
_logger = logging.getLogger(__name__)

# Tests set SYNCHRONOUS = True so background work runs inline and results are deterministic.
SYNCHRONOUS = False
_cleanup_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="chat-cleanup")
_task_pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="router-task")


def _load():
    """Baca chat_messages.json saat modul dimuat."""
    try:
        with open(STORE_FILE, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


_store = _load()  # {chat_id: {"all": [[message_id, unix_time], ...], "ephemeral": [message_id, ...]}}


def _save():
    """Tulis registry pesan ke chat_messages.json."""
    write_json_atomic(STORE_FILE, _store, indent=None)


def _chat(chat_id):
    """Ambil entri satu chat dan buang ID yang lebih tua dari MAX_AGE_SECONDS."""
    entry = _store.setdefault(str(chat_id), {"all": [], "ephemeral": []})
    now = time.time()
    entry["all"] = [item for item in entry["all"] if now - item[1] < MAX_AGE_SECONDS]
    fresh = {item[0] for item in entry["all"]}
    entry["ephemeral"] = [mid for mid in entry["ephemeral"] if mid in fresh]
    return entry


def _remember(chat_id, message_id, ephemeral):
    """Catat satu pesan; ephemeral=True berarti dihapus saat aksi berikutnya."""
    with _lock:
        entry = _chat(chat_id)
        if message_id not in {item[0] for item in entry["all"]}:
            entry["all"].append([message_id, time.time()])
        if ephemeral and message_id not in entry["ephemeral"]:
            entry["ephemeral"].append(message_id)
        _save()


def _forget(chat_id, message_ids):
    """Hapus ID pesan dari registry."""
    with _lock:
        entry = _chat(chat_id)
        drop = set(message_ids)
        entry["all"] = [item for item in entry["all"] if item[0] not in drop]
        entry["ephemeral"] = [mid for mid in entry["ephemeral"] if mid not in drop]
        _save()


def _delete_now(bot, chat_id, message_ids):
    """Panggil deleteMessage untuk tiap ID (abaikan error)."""
    for message_id in message_ids:
        try:
            bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception:
            pass  # already deleted, too old, or not found


def _delete(bot, chat_id, message_ids):
    """Lupakan pesan di registry sekarang, hapus di Telegram di latar belakang (tidak menunda balasan)."""
    message_ids = list(message_ids)
    if not message_ids:
        return
    _forget(chat_id, message_ids)
    if SYNCHRONOUS:
        _delete_now(bot, chat_id, message_ids)
    else:
        submit_quick(_delete_now, bot, chat_id, message_ids)


def submit_quick(function, *args):
    """Kirim pekerjaan singkat (hapus pesan, log admin) ke pool latar belakang."""
    return _cleanup_pool.submit(function, *args)


def in_background(function, *args, **kwargs):
    """Run slow work (router check) off the dispatcher thread, keeping this chat's message tracking."""
    if SYNCHRONOUS:
        return function(*args, **kwargs)
    chat_id, protected = _active_chat(), getattr(_local, "protected", None)

    def task():
        _local.chat_id, _local.protected = chat_id, protected
        _local.keep, _local.sent, _local.edited, _local.consumed = False, 0, set(), False
        try:
            function(*args, **kwargs)
        except Exception:
            _logger.exception("Background task %s failed", getattr(function, "__name__", function))
        finally:
            _local.chat_id = _local.protected = None

    _task_pool.submit(task)
    return None


def _active_chat():
    """Chat yang sedang diproses di thread ini, atau None."""
    return getattr(_local, "chat_id", None)


# ---------------------------------------------------------------- hooks used by the bot
def on_sent(message):
    """Called by TrackingBot for every message it sends."""
    chat = getattr(message, "chat", None)
    if message is None or chat is None or getattr(chat, "type", "private") != "private":
        return
    ephemeral = (message.chat_id == _active_chat()) and not getattr(_local, "keep", False)
    _remember(message.chat_id, message.message_id, ephemeral)
    if ephemeral:
        _local.sent = getattr(_local, "sent", 0) + 1


def on_edited(message_id):
    """Catat bahwa pesan ini diedit selama update berjalan (bukan diganti)."""
    edited = getattr(_local, "edited", None)
    if edited is not None and message_id is not None:
        edited.add(message_id)


def is_protected(message_id):
    """True for the log message whose button was pressed: never overwrite it."""
    return message_id is not None and message_id == getattr(_local, "protected", None)


def track_message(message):
    """Mark a message sent outside an update (e.g. startup notice) as temporary."""
    if message is not None:
        _remember(message.chat_id, message.message_id, True)


@contextmanager
def keep_messages():
    """Messages sent inside this block stay in the chat as a log."""
    previous = getattr(_local, "keep", False)
    _local.keep = True
    try:
        yield
    finally:
        _local.keep = previous


def mark_input_consumed():
    """A form used the user's message; it is deleted after handling."""
    _local.consumed = True


# ---------------------------------------------------------------- dispatcher handlers
def before_update(update, context):
    """Group -1: delete the previous temporary replies of this chat."""
    _local.chat_id = None
    chat = update.effective_chat
    if chat is None or chat.type != "private":
        return
    _local.chat_id = chat.id
    _local.keep = False
    _local.sent = 0
    _local.edited = set()
    _local.consumed = False
    _local.protected = None

    pressed = None
    query = update.callback_query
    if query is not None and query.message is not None:
        pressed = query.message.message_id
    with _lock:
        entry = _chat(chat.id)
        old = [mid for mid in entry["ephemeral"] if mid != pressed]
        if pressed is not None and pressed not in entry["ephemeral"]:
            _local.protected = pressed  # a log message: answer with a new message
    _delete(context.bot, chat.id, old)

    incoming = update.message
    if incoming is not None:
        _remember(chat.id, incoming.message_id, False)


def after_update(update, context):
    """Group 1: tidy up the pressed button message and the user's own input."""
    chat_id = _active_chat()
    if chat_id is None:
        return
    try:
        query = update.callback_query
        if query is not None and query.message is not None:
            pressed = query.message.message_id
            # The menu was replaced by new messages (not edited in place): remove it.
            if (pressed != getattr(_local, "protected", None) and pressed not in _local.edited
                    and _local.sent):
                _delete(context.bot, chat_id, [pressed])
        incoming = update.message
        if incoming is not None:
            is_command = bool(incoming.text and incoming.text.startswith("/"))
            if is_command or _local.consumed:
                _delete(context.bot, chat_id, [incoming.message_id])
    finally:
        _local.chat_id = None
        _local.protected = None


# ---------------------------------------------------------------- 🗑 Bersihkan
def clear_chat(bot, chat_id, keep_ids=()):
    """Delete every recorded message of the chat (bot replies, logs, user input)."""
    with _lock:
        ids = [item[0] for item in _chat(chat_id)["all"] if item[0] not in set(keep_ids)]
    _delete(bot, chat_id, ids)
    return len(ids)
