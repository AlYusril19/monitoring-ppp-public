"""Route free text to whichever form (wizard) is currently open for this chat."""
from configs.chat_tracker import mark_input_consumed
from handlers.handler_admin_settings import handle_admin_input
from handlers.handler_monitor_settings import handle_monitoring_input
from handlers.handler_onboarding import handle_onboarding_input
from handlers.handler_server import handle_server_wizard
from handlers.handler_start import handle_custom_server_input
from handlers.handler_traffic import handle_www_port_input
from handlers.handler_wallet import handle_manual_topup_input, handle_topup_custom_input

# Each handler returns True when it consumed the message.
WIZARDS = (
    handle_onboarding_input,
    handle_admin_input,
    handle_monitoring_input,
    handle_server_wizard,
    handle_custom_server_input,
    handle_manual_topup_input,
    handle_topup_custom_input,
    handle_www_port_input,
)


def handle_input(update, context):
    """Teks bebas: teruskan ke form yang sedang terbuka (WIZARDS); tanpa form → diam."""
    for wizard in WIZARDS:
        if wizard(update, context):
            mark_input_consumed()  # the user's answer is removed after handling
            return
    # No form is open: stay silent. Ordinary chat text must never trigger a reply.
