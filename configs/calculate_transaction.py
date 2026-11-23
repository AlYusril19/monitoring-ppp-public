from collections import defaultdict
from datetime import datetime

from configs.data_json_user import load_user_data


def calculate_monthly_transactions(user_id, year):
    """Return {month_number: {"income": x, "expenses": y}} for one user and year."""
    record = load_user_data().get(str(user_id))
    if not record:
        return {}
    monthly_summary = defaultdict(lambda: {"income": 0, "expenses": 0})
    for t in record.get("transactions", []):
        try:
            date = datetime.fromisoformat(t["date"])
        except (KeyError, ValueError):
            continue
        if date.year == year:
            amount = t.get("amount", 0)
            if amount > 0:
                monthly_summary[date.month]["income"] += amount
            else:
                monthly_summary[date.month]["expenses"] += abs(amount)
    return dict(monthly_summary)


def calculate_yearly_transactions(user_id, year):
    """Total (saldo masuk, pemakaian) satu user dalam setahun."""
    monthly_summary = calculate_monthly_transactions(user_id, year)
    yearly_income = sum(month["income"] for month in monthly_summary.values())
    yearly_expenses = sum(month["expenses"] for month in monthly_summary.values())
    return yearly_income, yearly_expenses
