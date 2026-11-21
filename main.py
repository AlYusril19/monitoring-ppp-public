from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler
from apscheduler.schedulers.background import BackgroundScheduler
from configs.send_message import bot
from handlers.handler_input import handle_input
from handlers.handler_start import start_command_handler, start_command_handler_by_custom
from handlers.handler_info import info_command_handler, infolengkap_command_handler
from handlers.handler_exit import exit_command_handler
from handlers.handler_traffic import monitoring_command_handler
from handlers.handler_version import version_command_handler
from handlers.handler_warning import warning
from handlers. handler_saldo_cek import cek_saldo
from handlers.handler_saldo_topup import topup
from handlers.handler_saldo_user import cek_semua_saldo
from handlers.handler_daftar import daftar
from handlers.handler_biaya import biaya_fitur
from handlers.handler_traffic import monitoring_command_handler
from handlers.handler_server import add_server, delete_server, edit_server
from handlers.handler_list_server import list_servers
from handlers.handler_connect_server import connect_to_server, server_name_handler, cancel, SERVER_NAME
from handlers.check_client_status_and_notify import check_client_status_and_notify
from handlers.handler_transaction import check_monthly_transactions, check_yearly_transactions
from handlers.handler_all_transaction import check_monthly_user_transactions, check_yearly_user_transactions
from handlers.handler_info import notify_command_handler
from handlers.send_startup_message import send_startup_message
from handlers.handler_user import aktifkan_user, user_aktif, arsipkan_user, user_arsip
from handlers.handler_menu import show_menu, menu_callback
from handlers.handler_monitor_settings import monitoring_settings
from handlers.handler_wallet import capture_payment_proof, set_qris_command
from handlers.handler_admin_settings import settings_command, set_price_command, set_role_command, set_trial_command

def main():
    # Inisialisasi bot Telegram
    updater = Updater(bot=bot)
    dp=updater.dispatcher

    # Tambahkan ConversationHandler untuk perintah /connect
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('connect', connect_to_server)],
        states={
            SERVER_NAME: [MessageHandler(Filters.text & ~Filters.command, server_name_handler)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    dp.add_handler(conv_handler)

    # Menambahkan handler untuk command /<perintah>
    dp.add_handler(CommandHandler('start', show_menu))
    dp.add_handler(CommandHandler('menu', show_menu))
    dp.add_handler(CommandHandler('exit', exit_command_handler))
    
    # Handler Informasi
    dp.add_handler(CommandHandler('why', warning))
    dp.add_handler(CommandHandler('infonotify', notify_command_handler))
    dp.add_handler(CommandHandler('info', infolengkap_command_handler))
    dp.add_handler(CommandHandler('version', version_command_handler))
    
    # List Server
    dp.add_handler(CommandHandler('custom', start_command_handler_by_custom))
    dp.add_handler(CommandHandler('listserver', list_servers))
    dp.add_handler(CommandHandler('addserver', add_server))
    dp.add_handler(CommandHandler('editserver', edit_server))
    dp.add_handler(CommandHandler('delserver', delete_server))
    # updater.dispatcher.add_handler(CommandHandler('connect', connect_to_server))
    
    # Monitoring Server
    dp.add_handler(CommandHandler('testppp', start_command_handler))
    dp.add_handler(CommandHandler('traffic', monitoring_command_handler))
    
    # Monitoring Manajemen Saldo
    dp.add_handler(CommandHandler('topup', topup))
    dp.add_handler(CommandHandler('saldo', cek_saldo))
    dp.add_handler(CommandHandler('daftar', daftar))
    dp.add_handler(CommandHandler('biaya', biaya_fitur))
    dp.add_handler(CommandHandler('monitoring', monitoring_settings))
    dp.add_handler(CommandHandler('historybulanan', check_monthly_transactions))
    dp.add_handler(CommandHandler('historytahunan', check_yearly_transactions))
    
    # Handler Manajemen Saldo Admin
    dp.add_handler(CommandHandler('saldouser', cek_semua_saldo))
    dp.add_handler(CommandHandler('laporanbulanan', check_monthly_user_transactions))
    dp.add_handler(CommandHandler('laporantahunan', check_yearly_user_transactions))
    dp.add_handler(CommandHandler('settings', settings_command))
    dp.add_handler(CommandHandler('setprice', set_price_command))
    dp.add_handler(CommandHandler('setrole', set_role_command))
    dp.add_handler(CommandHandler('settrial', set_trial_command))
    dp.add_handler(CommandHandler('setqris', set_qris_command))
    
    # Handler Manajemen User Aktif dan Arsip
    dp.add_handler(CommandHandler("arsipkan", arsipkan_user))
    dp.add_handler(CommandHandler("aktifkan", aktifkan_user))
    dp.add_handler(CommandHandler("useraktif", user_aktif))
    dp.add_handler(CommandHandler("userarsip", user_arsip))

    # Button callbacks are handled before free-form input so menus never leave
    # command-like text in the chat history.
    dp.add_handler(CallbackQueryHandler(menu_callback))
    dp.add_handler(MessageHandler(Filters.photo, capture_payment_proof))

    # Menambahkan handler untuk menerima input IP, username, dan password
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_input))

    # Scheduler untuk menjalankan fungsi secara periodik
    job_queue = updater.job_queue
    # The job wakes once a minute; each user uses their own normal/alert interval.
    job_queue.run_repeating(check_client_status_and_notify, interval=60, first=0)
    
    # Kirim pesan startup kepada semua pengguna
    send_startup_message(dp)
    
    # Memulai polling pesan dari Telegram
    updater.start_polling()

    # Menjaga agar program tetap berjalan
    updater.idle()
    

if __name__ == '__main__':
    main()
