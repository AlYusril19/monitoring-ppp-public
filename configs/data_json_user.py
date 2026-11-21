import json
import os

# Tentukan jalur lengkap ke file JSON relatif terhadap lokasi file main.py
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USER_DATA_FILE = os.path.join(BASE_DIR, "datauser.json")
NOTIFICATION_DATA_FILE = os.path.join(BASE_DIR, "last_notification_time.json")
APP_INFO_FILE = os.path.join(BASE_DIR, "app_info.json")


def load_user_data():
    try:
        with open(USER_DATA_FILE, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        # File kosong atau tidak valid JSON, kembali dictionary kosong
        return {}

def save_user_data(data):
    with open(USER_DATA_FILE, "w") as file:
        json.dump(data, file, indent=4)


def get_registered_username(user_id):
    """Return the display name recorded at registration, never live Telegram data."""
    record = load_user_data().get(str(user_id), {})
    return record.get("username_telegram") or record.get("nama") or str(user_id)

# Inisialisasi file JSON jika tidak ada atau kosong
for file in [USER_DATA_FILE, NOTIFICATION_DATA_FILE]:
    if not os.path.exists(file) or os.stat(file).st_size == 0:
        with open(file, "w") as f:
            json.dump({}, f, indent=4)

# Fungsi untuk mendapatkan waktu notifikasi terakhir
def get_last_notification_time(user_id):
    try:
        with open(NOTIFICATION_DATA_FILE, "r") as file:
            data = json.load(file)
        return data.get(str(user_id))
    except (FileNotFoundError, json.JSONDecodeError):
        return None

# Fungsi untuk menyimpan waktu notifikasi terakhir
def save_last_notification_time(user_id, last_notification_time):
    try:
        with open(NOTIFICATION_DATA_FILE, "r") as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    
    data[str(user_id)] = last_notification_time

    with open(NOTIFICATION_DATA_FILE, "w") as file:
        json.dump(data, file, indent=4)

def save_app_info(info):
    with open(APP_INFO_FILE, 'w') as file:
        json.dump(info, file, indent=4)

def load_app_info():
    if not os.path.exists(APP_INFO_FILE):
        return {}
    try:
        with open(APP_INFO_FILE, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
