from collections import defaultdict
from configs.data_json_user import load_user_data
from datetime import datetime

def calculate_monthly_transactions(user_id, year):
    user_data = load_user_data()
    if str(user_id) not in user_data:
        print(f"User ID {user_id} not found.")
        return {}

    transactions = user_data[str(user_id)].get("transactions", [])
    monthly_summary = defaultdict(lambda: {"income": 0, "expenses": 0})

    for t in transactions:
        date = datetime.fromisoformat(t["date"])
        if date.year == year:
            month = date.strftime('%B')
            amount = t["amount"]
            if amount > 0:
                monthly_summary[month]["income"] += amount
            else:
                monthly_summary[month]["expenses"] += abs(amount)

    return dict(monthly_summary)

def calculate_yearly_transactions(user_id, year):
    monthly_summary = calculate_monthly_transactions(user_id, year)
    yearly_income = sum(month["income"] for month in monthly_summary.values())
    yearly_expenses = sum(month["expenses"] for month in monthly_summary.values())

    return yearly_income, yearly_expenses