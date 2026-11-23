"""telegram.ext tiruan: cukup agar main.py bisa di-import saat uji."""


class _Handler:
    def __init__(self, *args, **kwargs):
        pass


CallbackQueryHandler = CommandHandler = MessageHandler = TypeHandler = Updater = _Handler


class Filters:
    text = photo = command = contact = None
