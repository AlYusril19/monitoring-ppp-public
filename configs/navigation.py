from telegram import InlineKeyboardButton, InlineKeyboardMarkup


# Every context.user_data key that means "the next text/photo is an answer to
# a form". /cancel and the ✖️ Batal button clear all of them in one place.
PENDING_INPUT_KEYS = (
    "onboarding_step",
    "monitoring_input_field",
    "server_wizard",
    "custom_server_wizard",
    "server_unverified",
    "www_port_input",
    "manual_topup_step",
    "manual_topup_user_id",
    "pending_topup_amount",
    "pending_topup_source",
    "topup_custom_input",
    "qris_upload",
    "admin_input",
)


def clear_pending_inputs(context):
    """Cancel any open form. Returns True when something was cancelled."""
    found = False
    for key in PENDING_INPUT_KEYS:
        if context.user_data.pop(key, None) is not None:
            found = True
    return found


class QueryFromMessage:
    """Lets a menu written for inline buttons open from a /command.

    Menu functions call query.answer() and query.edit_message_text(); for a
    command there is no button message to edit, so a new message is sent.
    """

    def __init__(self, update):
        self.from_user = update.effective_user
        self.message = update.effective_message
        self.data = ""

    def answer(self, *args, **kwargs):
        """Tidak melakukan apa pun (command tidak punya callback untuk dijawab)."""
        return None

    def edit_message_text(self, text, **kwargs):
        """Kirim pesan baru karena command tidak punya pesan tombol untuk diedit."""
        return self.message.reply_text(text, **kwargs)


def home_keyboard(label="🏠 Dashboard"):
    """Satu tombol 🏠 Dashboard (label bisa diganti)."""
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data="nav:home")]])


def session_action_keyboard():
    """Single action panel displayed after a completed router operation."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📡 Monitor PPPoE", callback_data="menu:pppoe"),
         InlineKeyboardButton("📈 Monitor Traffic", callback_data="menu:traffic")],
        [InlineKeyboardButton("🏠 Dashboard", callback_data="nav:home")],
    ])


def wizard_keyboard(kind):
    """Tombol ↩️ Reset Input + ✖️ Batal untuk form server."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("↩️ Reset Input", callback_data=f"input:reset:{kind}"),
         InlineKeyboardButton("✖️ Batal", callback_data="input:cancel")],
    ])


def cancel_keyboard():
    """For every prompt that waits for typed input."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("✖️ Batal", callback_data="input:cancel")]])


def back_keyboard(back_data, back_label="⬅️ Kembali"):
    """Back to the previous menu + Dashboard, for results inside a sub-menu."""
    return InlineKeyboardMarkup([[InlineKeyboardButton(back_label, callback_data=back_data),
                                  InlineKeyboardButton("🏠 Dashboard", callback_data="nav:home")]])


def topup_keyboard():
    """When the balance is not enough."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("💳 Isi Saldo", callback_data="menu:wallet"),
                                  InlineKeyboardButton("🏠 Dashboard", callback_data="nav:home")]])


def dashboard_row():
    """Satu baris berisi tombol 🏠 Dashboard, untuk ditambahkan ke keyboard lain."""
    return [InlineKeyboardButton("🏠 Dashboard", callback_data="nav:home")]
