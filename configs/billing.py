"""Single charging path so every transaction retains its price snapshot."""
from configs.add_transaction import add_transaction
from configs.app_settings import get_price, is_staff
from configs.data_json_user import load_user_data, save_user_data


def charge_user(user_id, feature):
    """Return ``(success, amount, remaining_balance)``.

    Staff accounts are not charged.  A failed charge never changes the
    balance, making button taps safe to retry.
    """
    amount = get_price(feature)
    if is_staff(user_id):
        return True, 0, None

    users = load_user_data()
    record = users.get(str(user_id))
    if not record:
        return False, amount, None
    balance = int(record.get("saldo", 0))
    if balance < amount:
        return False, amount, balance
    record["saldo"] = balance - amount
    save_user_data(users)
    add_transaction(user_id, -amount, feature, {"price": amount})
    return True, amount, record["saldo"]
