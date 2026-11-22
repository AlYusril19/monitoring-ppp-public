from datetime import datetime
from pytz import timezone
from configs.data_json_user import load_user_data
from configs.app_settings import is_staff
from configs.format_rupiah import format_rupiah

def check_monthly_user_transactions(update, context):
    user_id = update.effective_user.id
    user_data = load_user_data()

    if not is_staff(user_id):
        context.bot.send_message(chat_id=update.effective_chat.id, text="Akses ditolak.")
        return

    now = datetime.now(timezone('Asia/Jakarta'))

    args = getattr(context, "args", None) or []
    if len(args) == 1:
        try:
            selected_month = int(args[0])
            if selected_month < 1 or selected_month > 12:
                raise ValueError
        except ValueError:
            context.bot.send_message(chat_id=update.effective_chat.id, text="Format salah. Gunakan /laporanbulanan <bulan> (1-12)")
            return
    else:
        selected_month = now.month

    current_year = now.year

    total_income = 0
    total_outcome = 0
    report = ""

    for user_id, user_info in user_data.items():
        username = user_info.get("username_telegram", "Unknown")
        transactions = user_info.get("transactions", [])

        monthly_income = 0
        monthly_expense = 0

        for transaction in transactions:
            trans_date = datetime.fromisoformat(transaction["date"])

            if trans_date.year == current_year and trans_date.month == selected_month:
                if transaction.get("type") == "trial_balance":
                    continue
                if transaction["amount"] > 0:
                    monthly_income += transaction["amount"]
                else:
                    monthly_expense += abs(transaction["amount"])
        total_income += monthly_income
        total_outcome += monthly_expense
        if monthly_income > 0 or monthly_expense > 0:
            report += f"👤User {username} ({user_id})\n"
            report += f" Transaksi bulan {trans_date.strftime('%B')}:\n"
            report += f"   - Pemasukan: {format_rupiah(monthly_income)}\n"
            report += f"   - Pengeluaran: {format_rupiah(monthly_expense)}\n\n"
            
    report += f"Total Income : {format_rupiah(total_income)}\n"
    report += f"Total Outcome : {format_rupiah(total_outcome)}\n"
    report += "gunakan /laporanbulanan <bulan format angka> untuk bulan tertentu."
    if report:
        context.bot.send_message(chat_id=update.effective_chat.id, text=report)
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Tidak ada transaksi untuk bulan ini.")

def check_yearly_user_transactions(update, context):
    user_id = update.effective_user.id
    user_data = load_user_data()

    if not is_staff(user_id):
        context.bot.send_message(chat_id=update.effective_chat.id, text="Akses ditolak.")
        return

    now = datetime.now(timezone('Asia/Jakarta'))

    args = getattr(context, "args", None) or []
    if len(args) == 1:
        try:
            selected_year = int(args[0])
        except ValueError:
            context.bot.send_message(chat_id=update.effective_chat.id, text="Format salah. Gunakan /laporantahunan <tahun>")
            return
    else:
        selected_year = now.year

    total_income = 0
    total_outcome = 0
    report = ""

    for user_id_iter, user_info in user_data.items():  
        username = user_info.get("username_telegram", "Unknown")
        transactions = user_info.get("transactions", [])

        yearly_income = 0  # Reset nilai pendapatan tahunan untuk setiap pengguna
        yearly_expense = 0  # Reset nilai pengeluaran tahunan untuk setiap pengguna

        for transaction in transactions:
            trans_date = datetime.fromisoformat(transaction["date"])

            if trans_date.year == selected_year:
                if transaction.get("type") == "trial_balance":
                    continue
                if transaction["amount"] > 0:
                    yearly_income += transaction["amount"]
                else:
                    yearly_expense += abs(transaction["amount"])

        if yearly_income > 0 or yearly_expense > 0:
            report += f"👤User {username} ({user_id_iter})\n"  
            report += f"Transaksi tahun {selected_year}:\n"
            report += f"   - Pemasukan: {format_rupiah(yearly_income)}\n"
            report += f"   - Pengeluaran: {format_rupiah(yearly_expense)}\n\n"
        total_income += yearly_income
        total_outcome += yearly_expense
    
    report += f"Total Income {selected_year} : {format_rupiah(total_income)}\n"
    report += f"Total Outcome {selected_year} : {format_rupiah(total_outcome)}\n"
    report += "gunakan /tahunan <tahun> untuk tahun tertentu."
    if report:
        context.bot.send_message(chat_id=update.effective_chat.id, text=report)
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Tidak ada transaksi untuk tahun ini.")
