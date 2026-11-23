"""Telegram tiruan untuk uji regresi (bukan library asli).

Meniru bagian python-telegram-bot v13 yang dipakai bot, plus batas Telegram
(teks 4096, caption 1024). LIVE menyimpan pesan yang masih tampil per chat.
"""
import itertools

SENT = []    # (chat_id, text) setiap pesan/edit, berurutan
MARKUP = []  # reply_markup tiap pesan/edit
LIVE = {}    # chat_id -> {message_id: text} pesan yang masih ada di chat
_ids = itertools.count(100)


class Chat:
    def __init__(self, chat_id, type="private"):
        self.id = chat_id
        self.type = type

    def send_message(self, text, **kwargs):
        from configs.send_message import bot
        return bot.send_message(self.id, text, **kwargs)


class Msg:
    def __init__(self, chat_id, text="", photo=None, mid=None):
        self.chat_id = chat_id
        self.chat = Chat(chat_id)
        self.message_id = mid or next(_ids)
        self.text = text
        self.photo = photo
        LIVE.setdefault(chat_id, {})[self.message_id] = text

    def reply_text(self, text, **kwargs):
        from configs.send_message import bot
        return bot.send_message(self.chat_id, text, **kwargs)

    def delete(self):
        LIVE.get(self.chat_id, {}).pop(self.message_id, None)


class Bot:
    def __init__(self, token=None, **kwargs):
        pass

    def send_message(self, chat_id=None, text=None, *args, **kwargs):
        if text is None and args:
            text = args[0]
        if len(text) > 4096:
            raise Exception("Message is too long")
        SENT.append((chat_id, text))
        MARKUP.append(kwargs.get("reply_markup"))
        return Msg(chat_id, text)

    def send_document(self, chat_id=None, document=None, filename=None, caption=None, **kwargs):
        if caption and len(caption) > 1024:
            raise Exception("Message caption is too long")
        lines = document.getvalue().decode().count("\n") + 1
        text = f"[FILE {filename}: {lines} baris] {caption}"
        SENT.append((chat_id, text))
        MARKUP.append(kwargs.get("reply_markup"))
        return Msg(chat_id, text)

    def send_photo(self, chat_id=None, photo=None, **kwargs):
        text = "[FOTO] " + str(kwargs.get("caption", ""))
        SENT.append((chat_id, text))
        MARKUP.append(kwargs.get("reply_markup"))
        return Msg(chat_id, text, photo=[1])

    def delete_message(self, chat_id=None, message_id=None, **kwargs):
        if message_id not in LIVE.get(chat_id, {}):
            raise Exception("Message to delete not found")
        LIVE[chat_id].pop(message_id)

    def edit_message_text(self, text=None, chat_id=None, message_id=None, **kwargs):
        LIVE.setdefault(chat_id, {})[message_id] = text
        SENT.append((chat_id, text))
        MARKUP.append(kwargs.get("reply_markup"))
        return True


class InlineKeyboardButton:
    def __init__(self, text, callback_data=None, **kwargs):
        self.text = text
        self.callback_data = callback_data


class InlineKeyboardMarkup:
    def __init__(self, rows):
        self.rows = rows


class ReplyKeyboardRemove:
    pass


class KeyboardButton:
    def __init__(self, text, request_contact=None, **kwargs):
        self.text = text
        self.request_contact = request_contact


class ReplyKeyboardMarkup:
    def __init__(self, rows, **kwargs):
        self.rows = rows


class Update:
    pass
