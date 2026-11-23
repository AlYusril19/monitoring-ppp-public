from telegram import Bot
from dotenv import load_dotenv

import requests
from io import BytesIO
from configs.navigation import home_keyboard

import os

load_dotenv()

# Send Message to Users
telegram_bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
try:
    from telegram.ext import Defaults, ExtBot as _BaseBot
    _bot_kwargs = {"defaults": Defaults(quote=False)}
except ImportError:  # older library without ExtBot/Defaults
    _BaseBot, _bot_kwargs = Bot, {}

try:
    from telegram.utils.request import Request
except ImportError:  # test stubs
    Request = None

# PTB 13 gives a Bot built by hand a pool of ONE HTTP connection, and long polling
# (getUpdates) keeps it busy almost all the time. Every reply/edit/delete then had
# to open a new TLS connection to Telegram, which made each button slow. A real
# pool lets polling, replies, background deletes and the monitoring job each
# reuse a warm connection.
BOT_CONNECTION_POOL = 16


def _request(pool_size):
    """HTTP pool for a Bot (None in tests)."""
    if Request is None:
        return {}
    return {"request": Request(con_pool_size=pool_size, connect_timeout=10, read_timeout=20)}

from configs import chat_tracker


TEXT_LIMIT = 4096      # Telegram maximum for one text message
SAFE_TEXT_LIMIT = 3800
CAPTION_LIMIT = 1024   # Telegram maximum for a photo/document caption


def _split_text(text, limit=SAFE_TEXT_LIMIT):
    """Split on line breaks so each part fits in one Telegram message."""
    parts, current = [], ""
    for line in str(text).split("\n"):
        while len(line) > limit:  # a single very long line
            parts.append(line[:limit])
            line = line[limit:]
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > limit:
            parts.append(current)
            current = line
        else:
            current = candidate
    parts.append(current)
    return [part for part in parts if part]


class TrackingBot(_BaseBot):
    """Bot that records its messages so temporary replies can be cleaned up.

    quote=False: messages are never sent as a quoted reply to the user's message.
    See configs/chat_tracker.py for the cleanup rules.
    """

    def send_message(self, *args, **kwargs):
        """Kirim teks; teks > 4096 karakter otomatis dipecah. Pesan dicatat chat_tracker."""
        args = list(args)
        text = kwargs.get("text", args[1] if len(args) > 1 else "")
        if text and len(str(text)) > TEXT_LIMIT:
            # Never fail with "Message is too long": send it in parts, buttons on the last one.
            chat_id = kwargs.pop("chat_id", args[0] if args else None)
            markup = kwargs.pop("reply_markup", None)
            kwargs.pop("text", None)
            chunks = _split_text(text)
            message = None
            for index, chunk in enumerate(chunks):
                message = self.send_message(chat_id=chat_id, text=chunk,
                                            reply_markup=markup if index == len(chunks) - 1 else None, **kwargs)
            return message
        message = super().send_message(*args, **kwargs)
        chat_tracker.on_sent(message)
        return message

    def send_document(self, *args, **kwargs):
        """Kirim file dan catat di chat_tracker."""
        message = super().send_document(*args, **kwargs)
        chat_tracker.on_sent(message)
        return message

    def send_photo(self, *args, **kwargs):
        """Kirim foto dan catat di chat_tracker."""
        message = super().send_photo(*args, **kwargs)
        chat_tracker.on_sent(message)
        return message

    def edit_message_text(self, *args, **kwargs):
        """Edit pesan; bila targetnya log monitoring, kirim pesan baru agar log tidak tertimpa."""
        message_id = kwargs.get("message_id")
        if chat_tracker.is_protected(message_id):
            # Never overwrite a monitoring log: show the new screen as a new message.
            text = kwargs.get("text", args[0] if args else "")
            return self.send_message(chat_id=kwargs.get("chat_id"), text=text,
                                     parse_mode=kwargs.get("parse_mode"),
                                     reply_markup=kwargs.get("reply_markup"))
        try:
            result = super().edit_message_text(*args, **kwargs)
        except Exception as exc:
            # A button on a photo (e.g. QRIS) has no text to edit: show the screen as a new message.
            if "no text in the message" not in str(exc).lower():
                raise
            text = kwargs.get("text", args[0] if args else "")
            return self.send_message(chat_id=kwargs.get("chat_id"), text=text,
                                     parse_mode=kwargs.get("parse_mode"),
                                     reply_markup=kwargs.get("reply_markup"))
        chat_tracker.on_edited(message_id)
        return result


bot = TrackingBot(token=telegram_bot_token, **_bot_kwargs, **_request(BOT_CONNECTION_POOL))

# Send Message to Admin
chat_admin_ids = os.environ.get('ALLOWED_ADMIN_IDS')
allowed_admin_ids = set(map(int, chat_admin_ids.split(',')))

# Log Activity (Send Message to Admin)
telegram_bot_log_token = os.environ.get('TELEGRAM_BOT_LOG_TOKEN')
chat_log = int(os.environ.get('LOG_USER_ID'))


class _BackgroundLogBot(Bot):
    """Admin log bot: messages are sent in the background so a log never delays the user's reply."""

    def send_message(self, *args, **kwargs):
        """Kirim log tanpa menunggu (hasil tidak dipakai pemanggil)."""
        if chat_tracker.SYNCHRONOUS:
            return super().send_message(*args, **kwargs)
        chat_tracker.submit_quick(self._send_quietly, args, kwargs)
        return None

    def _send_quietly(self, args, kwargs):
        """Kirim log; kegagalan hanya dicetak."""
        try:
            Bot.send_message(self, *args, **kwargs)
        except Exception as exc:
            print(f"Gagal kirim log admin: {exc}")


bot_log = _BackgroundLogBot(token=telegram_bot_log_token, **_request(4))

def escape_md(value):
    """Escape text for Telegram legacy Markdown (parse_mode='markdown').

    PPPoE names, server names, interfaces and usernames often contain '_' or
    '*'; unescaped they make Telegram reject the whole message.
    """
    text = str(value)
    for char in ("_", "*", "`", "["):
        text = text.replace(char, "\\" + char)
    return text

# Send Message Text
def send_message(bot, chat_id, message, with_dashboard=False, reply_markup=None):
    """Send Markdown text. Final messages should pass with_dashboard=True or a reply_markup."""
    if reply_markup is None and with_dashboard:
        reply_markup = home_keyboard()
    return bot.send_message(chat_id=chat_id, text=message, parse_mode='markdown', reply_markup=reply_markup)

def fetch_image(image_url, timeout=15):
    """Download an image; return BytesIO, or None if it is not a usable image."""
    try:
        response = requests.get(image_url, timeout=timeout)
        if response.status_code != 200 or not response.content:
            return None
        if "image" not in response.headers.get("Content-Type", "image"):
            return None
        return BytesIO(response.content)
    except Exception as e:
        print("Error saat mengambil gambar:", str(e))
        return None


def send_down_report(bot, chat_id, header, down_users, footer, reply_markup=None):
    """Send a PPPoE DOWN list as ONE message, whatever its length.

    header/footer are Markdown text (dynamic parts already escaped).
    Short list → one text message with every name.
    Long list  → one document message: summary in the caption, full list in a .txt file.
    """
    count = len(down_users)
    lines = [f"❌ {escape_md(name)} - ({escape_md(last_out)})" for name, last_out in down_users]
    body = f"Client PPPoE *DOWN ({count} users)*:\n" + "\n".join(lines)
    text = "\n\n".join(part for part in (header, body, footer) if part)
    if len(text) <= SAFE_TEXT_LIMIT:
        return bot.send_message(chat_id=chat_id, text=text, parse_mode="markdown", reply_markup=reply_markup)

    content = "\n".join(f"{index}. {name} - ({last_out})"
                         for index, (name, last_out) in enumerate(down_users, 1))
    document = BytesIO(content.encode("utf-8"))
    filename = f"pppoe_down_{count}_users.txt"
    summary = f"Client PPPoE *DOWN ({count} users)*\n📎 Daftar lengkap ada di file terlampir."
    caption = "\n\n".join(part for part in (header, summary, footer) if part)
    parse_mode = "markdown"
    if len(caption) > CAPTION_LIMIT:
        caption = caption.replace("*", "").replace("\\", "")[:CAPTION_LIMIT]
        parse_mode = None
    return bot.send_document(chat_id=chat_id, document=document, filename=filename, caption=caption,
                             parse_mode=parse_mode, reply_markup=reply_markup)
