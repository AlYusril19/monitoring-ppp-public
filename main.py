from queue import Queue

from telegram import Update
from telegram.ext import (CallbackQueryHandler, CommandHandler, Dispatcher, Filters, JobQueue, MessageHandler,
                          TypeHandler, Updater)

from configs import chat_tracker
from configs.access import staff_only

from configs.data_json_user import DATA_LOCK, migrate_account_types
from configs.send_message import bot
from handlers.check_client_status_and_notify import check_client_status_and_notify
from handlers.handler_admin_settings import (set_max_server_command, set_price_command, set_role_command,
                                             set_trial_command, settings_command)
from handlers.handler_all_transaction import check_monthly_user_transactions, check_yearly_user_transactions
from handlers.handler_biaya import biaya_fitur
from handlers.handler_command_redirect import (add_server_command, cancel_command, daftar_command,
                                               servers_command, topup_command)
from handlers.handler_exit import exit_command_handler
from handlers.handler_info import infolengkap_command_handler, notify_command_handler
from handlers.handler_input import handle_input
from handlers.handler_menu import menu_callback, show_menu
from handlers.handler_onboarding import handle_contact
from handlers.handler_monitor_settings import monitoring_settings
from handlers.handler_saldo_cek import cek_saldo
from handlers.handler_start import start_command_handler, start_command_handler_by_custom
from handlers.handler_traffic import monitoring_command_handler
from handlers.handler_transaction import check_monthly_transactions, check_yearly_transactions
from handlers.handler_user import aktifkan_user, arsipkan_user, cek_semua_saldo, user_aktif, user_arsip
from handlers.handler_version import version_command_handler
from handlers.handler_wallet import capture_payment_proof, set_qris_command
from handlers.handler_warning import warning
from handlers.send_startup_message import send_startup_message

# command -> handler. Each command opens the same logic as its button.
COMMANDS = {
    # Navigasi & info
    "start": show_menu,
    "menu": show_menu,
    "cancel": cancel_command,
    "exit": exit_command_handler,
    "why": warning,
    "infonotify": notify_command_handler,
    "info": infolengkap_command_handler,
    "version": version_command_handler,
    "biaya": biaya_fitur,
    # Server (semua membuka menu Server Saya)
    "custom": start_command_handler_by_custom,
    "listserver": servers_command,
    "connect": servers_command,
    "editserver": servers_command,
    "delserver": servers_command,
    "addserver": add_server_command,
    # Monitoring
    "testppp": start_command_handler,
    "traffic": monitoring_command_handler,
    "monitoring": monitoring_settings,
    # Saldo user
    "saldo": cek_saldo,
    "topup": topup_command,
    "historybulanan": check_monthly_transactions,
    "historytahunan": check_yearly_transactions,
    # Admin
    "daftar": daftar_command,
    "saldouser": cek_semua_saldo,
    "laporanbulanan": check_monthly_user_transactions,
    "laporantahunan": check_yearly_user_transactions,
    "settings": settings_command,
    "setprice": set_price_command,
    "setrole": set_role_command,
    "settrial": set_trial_command,
    "setmaxserver": set_max_server_command,
    "setqris": set_qris_command,
    "arsipkan": arsipkan_user,
    "aktifkan": aktifkan_user,
    "useraktif": user_aktif,
    "userarsip": user_arsip,
}

# Staff-only commands: checked centrally (configs/access.py) before the handler runs.
STAFF_COMMANDS = {
    "saldouser", "laporanbulanan", "laporantahunan", "settings", "setprice", "setrole", "settrial",
    "setmaxserver", "setqris", "arsipkan", "aktifkan", "useraktif", "userarsip",
}


class LockedDispatcher(Dispatcher):
    """Handles one update at a time while holding DATA_LOCK.

    Handlers do load → modify → save on the JSON files; holding the lock for the
    whole update keeps background router tasks and the monitoring job from
    writing in between. Slow router work leaves the dispatcher through
    chat_tracker.in_background, so the lock is only held for quick work.
    """

    def process_update(self, update):
        """Proses satu update sambil memegang DATA_LOCK."""
        with DATA_LOCK:
            super().process_update(update)


def main():
    # Add the admin/client marker to records created by earlier releases.
    """Daftarkan semua handler, scheduler monitoring, lalu jalankan bot (polling)."""
    migrate_account_types()
    job_queue = JobQueue()
    dp = LockedDispatcher(bot, Queue(), job_queue=job_queue, workers=4)
    job_queue.set_dispatcher(dp)
    updater = Updater(dispatcher=dp, workers=None)  # workers are set on the dispatcher

    # Group -1 / 1 wrap every update: delete the previous temporary replies first,
    # then the pressed menu and the user's own input (configs/chat_tracker.py).
    dp.add_handler(TypeHandler(Update, chat_tracker.before_update), group=-1)
    dp.add_handler(TypeHandler(Update, chat_tracker.after_update), group=1)

    for name, handler in COMMANDS.items():
        dp.add_handler(CommandHandler(name, staff_only(handler) if name in STAFF_COMMANDS else handler))

    # All inline buttons go through one router (prefix-based, see docs/ALUR-FITUR.md).
    dp.add_handler(CallbackQueryHandler(menu_callback))
    # Photos: payment proof, or a new QRIS from a superadmin.
    dp.add_handler(MessageHandler(Filters.photo, capture_payment_proof))
    # Shared contact: phone verification for registration (handlers/handler_onboarding.py).
    dp.add_handler(MessageHandler(Filters.contact, handle_contact))
    # Free text: answers to whichever form is open (handlers/handler_input.py).
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_input))

    # The job wakes once a minute; each user uses their own normal/alert interval.
    updater.job_queue.run_repeating(check_client_status_and_notify, interval=60, first=0)

    send_startup_message(dp)
    # Ignore messages sent while the bot was offline, so it does not answer a
    # backlog of old chat messages right after starting.
    updater.start_polling(drop_pending_updates=True)
    updater.idle()


if __name__ == '__main__':
    main()
