"""Transaction history for the user's own account (/historybulanan, /historytahunan, 📜 buttons)."""
from datetime import datetime

from configs.calculate_transaction import calculate_monthly_transactions, calculate_yearly_transactions
from configs.format_rupiah import format_rupiah
from configs.navigation import home_keyboard

MONTHS = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
          "Agustus", "September", "Oktober", "November", "Desember"]


def _year_from(context):
    """Tahun dari argumen command, default tahun ini; None bila tidak valid."""
    args = getattr(context, "args", None) or []
    try:
        return int(args[0]) if args else datetime.now().year
    except ValueError:
        return None


def check_monthly_transactions(update, context):
    """/historybulanan dan tombol 📜: riwayat per bulan milik user."""
    year = _year_from(context)
    if year is None:
        update.effective_message.reply_text("Gunakan: /historybulanan <tahun>", reply_markup=home_keyboard())
        return
    summary = calculate_monthly_transactions(update.effective_user.id, year)
    if not summary:
        text = f"Belum ada transaksi di tahun {year}."
    else:
        lines = [f"📜 Riwayat per bulan {year}"]
        for month in sorted(summary):
            item = summary[month]
            lines.append(f"\n{MONTHS[month - 1]}\n  - Saldo masuk: {format_rupiah(item['income'])}\n"
                         f"  - Pemakaian: {format_rupiah(item['expenses'])}")
        text = "\n".join(lines)
    context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=home_keyboard())


def check_yearly_transactions(update, context):
    """/historytahunan dan tombol 📜: total setahun milik user."""
    year = _year_from(context)
    if year is None:
        update.effective_message.reply_text("Gunakan: /historytahunan <tahun>", reply_markup=home_keyboard())
        return
    income, expenses = calculate_yearly_transactions(update.effective_user.id, year)
    text = (f"📜 Total transaksi tahun {year}:\n"
            f"  - Saldo masuk: {format_rupiah(income)}\n"
            f"  - Pemakaian: {format_rupiah(expenses)}")
    context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=home_keyboard())
