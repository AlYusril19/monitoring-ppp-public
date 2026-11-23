"""Revenue reports for staff (/laporanbulanan, /laporantahunan, 📊/📈 buttons).

Income  = saldo masuk (topup, topup_request, manual_topup); trial is excluded.
Outcome = pemakaian layanan (testppp, traffic, notify).
"""
from datetime import datetime

from pytz import timezone

from configs.app_settings import is_staff
from configs.data_json_user import load_user_data
from configs.format_rupiah import format_rupiah
from configs.navigation import home_keyboard

MONTHS = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
          "Agustus", "September", "Oktober", "November", "Desember"]


def _totals(transactions, year, month=None):
    """Jumlahkan saldo masuk & pemakaian dari daftar transaksi (trial diabaikan)."""
    income = expense = 0
    for transaction in transactions:
        if transaction.get("type") == "trial_balance":
            continue
        try:
            date = datetime.fromisoformat(transaction["date"])
        except (KeyError, ValueError):
            continue
        if date.year != year or (month is not None and date.month != month):
            continue
        amount = transaction.get("amount", 0)
        if amount > 0:
            income += amount
        else:
            expense += abs(amount)
    return income, expense


def _report(update, context, year, month=None):
    """Susun dan kirim laporan semua user untuk satu tahun / bulan."""
    chat_id = update.effective_chat.id
    if not is_staff(update.effective_user.id):
        context.bot.send_message(chat_id=chat_id, text="Akses ditolak.", reply_markup=home_keyboard())
        return
    period = f"{MONTHS[month - 1]} {year}" if month else str(year)
    lines, total_income, total_expense = [], 0, 0
    for user_id, record in load_user_data().items():
        income, expense = _totals(record.get("transactions", []), year, month)
        total_income += income
        total_expense += expense
        if income or expense:
            lines.append(f"👤 {record.get('username_telegram', 'Unknown')} ({user_id})\n"
                         f"   - Saldo masuk: {format_rupiah(income)}\n"
                         f"   - Pemakaian: {format_rupiah(expense)}")
    body = "\n\n".join(lines) if lines else "Tidak ada transaksi pada periode ini."
    usage = "/laporanbulanan <bulan 1-12>" if month else "/laporantahunan <tahun>"
    text = (f"📊 Laporan {period}\n\n{body}\n\n"
            f"Total saldo masuk: {format_rupiah(total_income)}\n"
            f"Total pemakaian: {format_rupiah(total_expense)}\n"
            f"(saldo trial tidak dihitung)\n\nPeriode lain: {usage}")
    context.bot.send_message(chat_id=chat_id, text=text, reply_markup=home_keyboard())


def check_monthly_user_transactions(update, context):
    """/laporanbulanan [bulan] dan tombol 📊."""
    now = datetime.now(timezone("Asia/Jakarta"))
    args = getattr(context, "args", None) or []
    month = now.month
    if args:
        try:
            month = int(args[0])
            if not 1 <= month <= 12:
                raise ValueError
        except ValueError:
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text="Format salah. Gunakan /laporanbulanan <bulan> (1-12)",
                                     reply_markup=home_keyboard())
            return
    _report(update, context, now.year, month)


def check_yearly_user_transactions(update, context):
    """/laporantahunan [tahun] dan tombol 📈."""
    now = datetime.now(timezone("Asia/Jakarta"))
    args = getattr(context, "args", None) or []
    year = now.year
    if args:
        try:
            year = int(args[0])
        except ValueError:
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text="Format salah. Gunakan /laporantahunan <tahun>",
                                     reply_markup=home_keyboard())
            return
    _report(update, context, year)
