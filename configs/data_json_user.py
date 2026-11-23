"""JSON storage (datauser.json, app_info.json).

Several threads touch these files (the update dispatcher, background router
checks, the monitoring job), so:
  * every read/write holds DATA_LOCK (re-entrant), and main.py holds it for the
    whole handling of one Telegram update, so a handler's load → save is never
    interleaved with another thread's write;
  * writes are atomic (temp file + os.replace): a reader never sees a half
    written file (which used to read as {} and could wipe the data on save).
Code that does its own load → modify → save outside an update (background
tasks, the job) wraps that block in ``with DATA_LOCK:``.
"""
import json
import os
import threading

# Tentukan jalur lengkap ke file JSON relatif terhadap lokasi file main.py
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USER_DATA_FILE = os.path.join(BASE_DIR, "datauser.json")
APP_INFO_FILE = os.path.join(BASE_DIR, "app_info.json")

DATA_LOCK = threading.RLock()


def write_json_atomic(path, data, indent=4):
    """Tulis JSON ke file sementara lalu ganti file asli sekaligus (tidak pernah setengah jadi)."""
    temp = f"{path}.tmp"
    with open(temp, "w") as file:
        json.dump(data, file, indent=indent)
    os.replace(temp, path)


def _read_json(path):
    """Baca file JSON; {} bila belum ada atau rusak."""
    try:
        with open(path, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def migrate_account_types():
    """Mark existing records as admin/client without changing balances or servers."""
    with DATA_LOCK:
        users = load_user_data()
        admin_ids = {item.strip() for item in os.environ.get("ALLOWED_ADMIN_IDS", "").split(",") if item.strip()}
        changed = False
        for user_id, record in users.items():
            if "account_type" not in record:
                record["account_type"] = "admin" if user_id in admin_ids else "client"
                changed = True
        if changed:
            save_user_data(users)


def load_user_data():
    """Baca datauser.json; {} bila belum ada/rusak."""
    with DATA_LOCK:
        return _read_json(USER_DATA_FILE)


def save_user_data(data):
    """Tulis seluruh datauser.json (atomik)."""
    with DATA_LOCK:
        write_json_atomic(USER_DATA_FILE, data)


def get_registered_username(user_id):
    """Return the display name recorded at registration, never live Telegram data."""
    record = load_user_data().get(str(user_id), {})
    return record.get("username_telegram") or record.get("nama") or str(user_id)


# Inisialisasi file JSON jika tidak ada atau kosong
for file in [USER_DATA_FILE]:
    if not os.path.exists(file) or os.stat(file).st_size == 0:
        with open(file, "w") as f:
            json.dump({}, f, indent=4)


def save_app_info(info):
    """Tulis seluruh app_info.json (pengaturan & antrian, atomik)."""
    with DATA_LOCK:
        write_json_atomic(APP_INFO_FILE, info)


def load_app_info():
    """Baca app_info.json; {} bila belum ada/rusak."""
    with DATA_LOCK:
        return _read_json(APP_INFO_FILE)
