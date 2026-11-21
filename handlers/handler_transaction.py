from telegram.ext import CommandHandler
from configs.calculate_transaction import calculate_monthly_transactions, calculate_yearly_transactions
from datetime import datetime
from configs.format_rupiah import format_rupiah

def check_monthly_transactions(update, context):
    user_id = update.effective_user.id
    year = int(context.args[0]) if context.args else datetime.now().year
    monthly_summary = calculate_monthly_transactions(user_id, year)
    
    for month, summary in monthly_summary.items():
        message = f"Transaksi bulan {month}:\n"
        message += f"  - Pemasukan: {format_rupiah(summary['income'])}\n"\
                   f"  - Pengeluaran: {format_rupiah(summary['expenses'])}"
    
    context.bot.send_message(chat_id=update.effective_chat.id, text=message)

def check_yearly_transactions(update, context):
    user_id = update.effective_user.id
    year = int(context.args[0]) if context.args else datetime.now().year
    yearly_income, yearly_expenses = calculate_yearly_transactions(user_id, year)
    
    message = f"Total transaksi tahun {year}:\n" \
              f"  - Pemasukan: {format_rupiah(yearly_income)}\n" \
              f"  - Pengeluaran: {format_rupiah(yearly_expenses)}"
    
    context.bot.send_message(chat_id=update.effective_chat.id, text=message)