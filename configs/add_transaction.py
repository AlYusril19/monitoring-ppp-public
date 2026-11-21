from configs.data_json_user import load_user_data, save_user_data
from configs.get_current_time import get_current_time

def add_transaction(user_id, amount, transaction_type, metadata=None):
    user_data = load_user_data()
    date = get_current_time()
    transaction = {
        "date": date,
        "amount": amount,
        "type": transaction_type
    }
    if metadata:
        transaction["metadata"] = metadata

    if str(user_id) in user_data:
        if "transactions" not in user_data[str(user_id)]:
            user_data[str(user_id)]["transactions"] = []
        
        user_data[str(user_id)]["transactions"].append(transaction)
        save_user_data(user_data)
    else:
        print(f"User ID {user_id} not found.")
