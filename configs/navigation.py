from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def home_keyboard(label="🏠 Dashboard"):
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data="nav:home")]])


def session_action_keyboard():
    """Single action panel displayed after a completed router operation."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📡 Monitor PPPoE", callback_data="menu:pppoe"),
         InlineKeyboardButton("📈 Monitor Traffic", callback_data="menu:traffic")],
        [InlineKeyboardButton("🏠 Dashboard", callback_data="nav:home")],
    ])


def wizard_keyboard(kind):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("↩️ Reset Input", callback_data=f"input:reset:{kind}"),
         InlineKeyboardButton("✖️ Batal", callback_data="input:cancel")],
    ])
