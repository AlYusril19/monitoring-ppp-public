from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def home_keyboard(label="🏠 Dashboard"):
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data="nav:home")]])
