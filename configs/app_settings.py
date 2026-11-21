"""Persistent, Telegram-managed application settings.

This module deliberately keeps operational settings out of source code.  The
JSON file is small and backwards compatible with the existing installation.
"""
from copy import deepcopy

from configs.data_json_user import load_app_info, save_app_info
from configs.send_message import allowed_admin_ids


DEFAULT_SETTINGS = {
    "prices": {
        "testppp": 125,
        "traffic": 50,
        "notify": 250,
    },
    "monitoring": {
        "normal_interval_minutes": 20,
        "alert_interval_minutes": 120,
    },
    "trial_balance": 5000,
    "qris_file_id": None,
    "roles": {},
}


def load_settings():
    settings = deepcopy(DEFAULT_SETTINGS)
    saved = load_app_info().get("settings", {})
    for key in ("prices", "monitoring", "roles"):
        if isinstance(saved.get(key), dict):
            settings[key].update(saved[key])
    if isinstance(saved.get("trial_balance"), int) and saved["trial_balance"] >= 0:
        settings["trial_balance"] = saved["trial_balance"]
    if isinstance(saved.get("qris_file_id"), str):
        settings["qris_file_id"] = saved["qris_file_id"]
    return settings


def save_settings(settings):
    app_info = load_app_info()
    app_info["settings"] = settings
    save_app_info(app_info)


def get_role(user_id):
    if int(user_id) in allowed_admin_ids:
        return "superadmin"
    return load_settings()["roles"].get(str(user_id), "user")


def is_staff(user_id):
    return get_role(user_id) in {"superadmin", "admin", "operator"}


def is_superadmin(user_id):
    return get_role(user_id) == "superadmin"


def get_price(feature):
    return int(load_settings()["prices"].get(feature, 0))


def set_price(feature, amount):
    settings = load_settings()
    settings["prices"][feature] = int(amount)
    save_settings(settings)


def set_role(user_id, role):
    if role not in {"user", "operator", "admin"}:
        raise ValueError("Role harus user, operator, atau admin")
    settings = load_settings()
    if role == "user":
        settings["roles"].pop(str(user_id), None)
    else:
        settings["roles"][str(user_id)] = role
    save_settings(settings)


def get_trial_balance():
    return int(load_settings()["trial_balance"])


def set_trial_balance(amount):
    settings = load_settings()
    settings["trial_balance"] = int(amount)
    save_settings(settings)


def get_qris_file_id():
    return load_settings().get("qris_file_id")


def set_qris_file_id(file_id):
    settings = load_settings()
    settings["qris_file_id"] = file_id
    save_settings(settings)


def get_monitoring_config(user_record):
    config = load_settings()["monitoring"].copy()
    config.update(user_record.get("monitoring", {}))
    return config

