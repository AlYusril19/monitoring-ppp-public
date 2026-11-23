"""Persistent, Telegram-managed application settings.

Every operational value that an admin can change lives here, with one default
in DEFAULT_SETTINGS. The defaults are used whenever app_info.json has no value
(for example right after a database reset), so the bot always works without
any admin input.
"""
from copy import deepcopy

from configs.data_json_user import load_app_info, save_app_info
from configs.send_message import allowed_admin_ids


# Features that are billed through configs/billing.charge_user().
PRICE_LABELS = {
    "testppp": "Cek PPPoE",
    "traffic": "Monitor Traffic",
    "notify": "Notifikasi down",
}

DEFAULT_SETTINGS = {
    "prices": {
        "testppp": 125,
        "traffic": 50,
        "notify": 250,
    },
    "monitoring": {
        # How often the router is checked.
        "normal_interval_minutes": 20,
        # After a charged notification: repeat (and charge) again only after this delay.
        "alert_interval_minutes": 120,
        # Stage 1 (⚠️) triggers the automatic notification; stage 2 (🚨) escalates.
        "warning_threshold": 6,
        "critical_threshold": 12,
        # Global profiles excluded for every user (admin-managed).
        "excluded_profiles": ["expired", "pribadi-home"],
    },
    "trial_balance": 5000,
    # manual = admin chooses at approval, auto = every eligible approval gets it, off = never.
    "trial_mode": "manual",
    "registration": {
        # Max new registration requests per hour from all users (0 = unlimited).
        "hourly_limit": 10,
        # A rejected user may apply again only after this many hours.
        "reject_cooldown_hours": 24,
    },
    "max_servers": 5,
    # Topup packages: one static QRIS image per nominal (qris_file_id None -> the general QRIS).
    "topup_packages": [{"amount": amount, "qris_file_id": None}
                       for amount in (5000, 10000, 25000, 50000, 100000)],
    # User-typed nominal ("Nominal Lain"), paid with the general QRIS below.
    "topup_custom": {"min": 10000, "max": 1000000},
    # General QRIS without a fixed nominal (custom amount + fallback for packages).
    "qris_file_id": None,
    # Part of the paid (non-trial) balance returned as money when an account is deleted.
    "refund_percent": 0,
    "roles": {},
}

TRIAL_MODES = {
    "manual": "Manual (admin memilih saat approval)",
    "auto": "Otomatis (setiap approval yang memenuhi syarat)",
    "off": "Nonaktif (tanpa trial)",
}


def load_settings():
    """Gabungkan DEFAULT_SETTINGS dengan app_info.json → settings; selalu mengembalikan nilai lengkap."""
    settings = deepcopy(DEFAULT_SETTINGS)
    saved = load_app_info().get("settings", {})
    for key in ("prices", "monitoring", "roles", "registration", "topup_custom"):
        if isinstance(saved.get(key), dict):
            settings[key].update(saved[key])
    for key in ("trial_balance", "max_servers", "refund_percent"):
        if isinstance(saved.get(key), int) and saved[key] >= 0:
            settings[key] = saved[key]
    if saved.get("trial_mode") in TRIAL_MODES:
        settings["trial_mode"] = saved["trial_mode"]
    packages = _clean_packages(saved.get("topup_packages"))
    if packages is None:
        # Data from before 2.3.0: nominal list without a QRIS per nominal.
        amounts = saved.get("topup_amounts")
        if isinstance(amounts, list) and amounts and all(isinstance(a, int) and a > 0 for a in amounts):
            packages = [{"amount": a, "qris_file_id": None} for a in sorted(set(amounts))]
    if packages is not None:
        settings["topup_packages"] = packages
    if isinstance(saved.get("qris_file_id"), str):
        settings["qris_file_id"] = saved["qris_file_id"]
    return settings


def _clean_packages(packages):
    """Validasi daftar paket topup tersimpan; None bila tidak ada/rusak ([] tetap sah)."""
    if not isinstance(packages, list):
        return None
    result, seen = [], set()
    for item in packages:
        if not isinstance(item, dict):
            continue
        amount = item.get("amount")
        if not isinstance(amount, int) or amount <= 0 or amount in seen:
            continue
        seen.add(amount)
        qris = item.get("qris_file_id")
        result.append({"amount": amount, "qris_file_id": qris if isinstance(qris, str) else None})
    return sorted(result, key=lambda item: item["amount"])


def save_settings(settings):
    """Simpan dict settings ke app_info.json (data lain di file itu dipertahankan)."""
    app_info = load_app_info()
    app_info["settings"] = settings
    save_app_info(app_info)


def _update_setting(key, value):
    """Ubah satu key settings lalu simpan."""
    settings = load_settings()
    settings[key] = value
    save_settings(settings)


# ---------------------------------------------------------------- roles
def get_role(user_id):
    """Role user: superadmin (.env), admin/operator (settings.roles), atau user."""
    if int(user_id) in allowed_admin_ids:
        return "superadmin"
    return load_settings()["roles"].get(str(user_id), "user")


def is_staff(user_id):
    """True untuk superadmin, admin, dan operator (tidak dipotong biaya, boleh approval)."""
    return get_role(user_id) in {"superadmin", "admin", "operator"}


def is_superadmin(user_id):
    """True hanya untuk ID di ALLOWED_ADMIN_IDS (.env)."""
    return get_role(user_id) == "superadmin"


def staff_ids():
    """Superadmins from .env plus admin/operator roles set via Telegram."""
    roles = load_settings()["roles"]
    return set(allowed_admin_ids) | {int(uid) for uid, role in roles.items() if role in {"admin", "operator"}}


def set_role(user_id, role):
    """Atur role admin/operator/user; juga menandai account_type di datauser.json."""
    if role not in {"user", "operator", "admin"}:
        raise ValueError("Role harus user, operator, atau admin")
    settings = load_settings()
    if role == "user":
        settings["roles"].pop(str(user_id), None)
    else:
        settings["roles"][str(user_id)] = role
    save_settings(settings)
    # Keep the account type visible in datauser.json for administrators.
    from configs.data_json_user import load_user_data, save_user_data
    users = load_user_data()
    if str(user_id) in users:
        users[str(user_id)]["account_type"] = "client" if role == "user" else "admin"
        save_user_data(users)


# ---------------------------------------------------------------- prices
def get_price(feature):
    """Harga fitur (testppp/traffic/notify) dalam rupiah."""
    return int(load_settings()["prices"].get(feature, 0))


def set_price(feature, amount):
    """Ubah harga satu fitur yang ada di PRICE_LABELS."""
    if feature not in PRICE_LABELS:
        raise ValueError(f"Fitur harus salah satu dari: {', '.join(PRICE_LABELS)}")
    settings = load_settings()
    settings["prices"][feature] = int(amount)
    save_settings(settings)


def price_summary():
    """One price list text, reused by /biaya, /settings and the admin menu."""
    prices = load_settings()["prices"]
    return "\n".join(f"- {label}: Rp{int(prices.get(key, 0)):,}" for key, label in PRICE_LABELS.items())


# ---------------------------------------------------------------- balance & topup
def get_trial_balance():
    """Saldo trial untuk registrasi yang disetujui dengan trial."""
    return int(load_settings()["trial_balance"])


def set_trial_balance(amount):
    """Ubah saldo trial registrasi."""
    _update_setting("trial_balance", int(amount))


def get_trial_mode():
    """Mode pemberian trial: manual / auto / off (lihat TRIAL_MODES)."""
    return load_settings()["trial_mode"]


def set_trial_mode(mode):
    """Ubah mode pemberian trial."""
    if mode not in TRIAL_MODES:
        raise ValueError("Mode trial harus manual, auto, atau off.")
    _update_setting("trial_mode", mode)


def get_registration_limits():
    """{'hourly_limit', 'reject_cooldown_hours'} untuk keamanan registrasi (nilai >= 0)."""
    limits = load_settings()["registration"]
    result = {}
    for key, default in DEFAULT_SETTINGS["registration"].items():
        try:
            result[key] = max(0, int(limits.get(key, default)))
        except (TypeError, ValueError):
            result[key] = default
    return result


def set_registration_limit(key, value):
    """Ubah satu batas registrasi (hourly_limit / reject_cooldown_hours), nilai >= 0."""
    if key not in DEFAULT_SETTINGS["registration"]:
        raise ValueError("Batas registrasi tidak dikenal.")
    if int(value) < 0:
        raise ValueError("Nilai minimal 0.")
    settings = load_settings()
    settings["registration"][key] = int(value)
    save_settings(settings)


def get_refund_percent():
    """Persentase saldo berbayar yang direfund sebagai uang saat akun dihapus (0-100)."""
    return min(100, int(load_settings()["refund_percent"]))


def set_refund_percent(percent):
    """Ubah persentase refund (0-100)."""
    percent = int(percent)
    if not 0 <= percent <= 100:
        raise ValueError("Persentase refund harus 0 sampai 100.")
    _update_setting("refund_percent", percent)


MAX_TOPUP_PACKAGES = 12


def get_topup_packages():
    """Paket topup [{'amount', 'qris_file_id'}], urut nominal."""
    return [dict(item) for item in load_settings()["topup_packages"]]


def get_topup_package(amount):
    """Satu paket topup berdasarkan nominal, atau None."""
    return next((item for item in get_topup_packages() if item["amount"] == int(amount)), None)


def get_topup_amounts():
    """Nominal semua paket topup."""
    return [item["amount"] for item in get_topup_packages()]


def _save_packages(packages):
    """Simpan daftar paket (urut nominal)."""
    _update_setting("topup_packages", sorted(packages, key=lambda item: item["amount"]))


def add_topup_package(amount, qris_file_id):
    """Tambah paket nominal baru beserta QRIS statiknya."""
    amount = int(amount)
    packages = get_topup_packages()
    if amount <= 0:
        raise ValueError("Nominal harus lebih dari nol.")
    if any(item["amount"] == amount for item in packages):
        raise ValueError(f"Paket Rp{amount:,} sudah ada.")
    if len(packages) >= MAX_TOPUP_PACKAGES:
        raise ValueError(f"Maksimal {MAX_TOPUP_PACKAGES} paket.")
    packages.append({"amount": amount, "qris_file_id": qris_file_id})
    _save_packages(packages)


def update_topup_package(amount, new_amount=None, qris_file_id=None):
    """Ubah nominal dan/atau QRIS satu paket."""
    packages = get_topup_packages()
    package = next((item for item in packages if item["amount"] == int(amount)), None)
    if package is None:
        raise ValueError("Paket tidak ditemukan.")
    if new_amount is not None:
        new_amount = int(new_amount)
        if new_amount <= 0:
            raise ValueError("Nominal harus lebih dari nol.")
        if new_amount != package["amount"] and any(item["amount"] == new_amount for item in packages):
            raise ValueError(f"Paket Rp{new_amount:,} sudah ada.")
        package["amount"] = new_amount
    if qris_file_id is not None:
        package["qris_file_id"] = qris_file_id
    _save_packages(packages)


def delete_topup_package(amount):
    """Hapus satu paket topup."""
    packages = get_topup_packages()
    remaining = [item for item in packages if item["amount"] != int(amount)]
    if len(remaining) == len(packages):
        raise ValueError("Paket tidak ditemukan.")
    _save_packages(remaining)


def get_custom_topup_range():
    """(min, max) nominal bebas yang boleh diketik user."""
    custom = load_settings()["topup_custom"]
    return int(custom.get("min", 1)), int(custom.get("max", 0))


def set_custom_topup_range(minimum, maximum):
    """Ubah batas nominal bebas (min >= 1, max > min)."""
    minimum, maximum = int(minimum), int(maximum)
    if minimum < 1 or maximum <= minimum:
        raise ValueError("Batas tidak valid: min minimal 1 dan max harus lebih besar dari min.")
    _update_setting("topup_custom", {"min": minimum, "max": maximum})


def get_qris_file_id():
    """file_id QRIS umum (nominal bebas & cadangan paket tanpa QRIS), atau None."""
    return load_settings().get("qris_file_id")


def set_qris_file_id(file_id):
    """Simpan file_id QRIS umum."""
    _update_setting("qris_file_id", file_id)


def package_qris(amount):
    """QRIS satu paket: QRIS paket itu, atau QRIS umum sebagai cadangan."""
    package = get_topup_package(amount)
    return (package or {}).get("qris_file_id") or get_qris_file_id()


# ---------------------------------------------------------------- servers
def get_max_servers():
    """Batas global jumlah Server Saya per user (default 5)."""
    return int(load_settings()["max_servers"])


def set_max_servers(amount):
    """Ubah batas global jumlah server (minimal 1)."""
    if int(amount) < 1:
        raise ValueError("Batas server minimal 1.")
    _update_setting("max_servers", int(amount))


def get_server_limit(user_id):
    """Maximum saved servers for this user.

    Single hook for future paid plans: when packages are added, resolve the
    user's package here; every caller already goes through this function.
    """
    return get_max_servers()


# ---------------------------------------------------------------- monitoring
def get_global_excluded_profiles():
    """Profile PPPoE yang dikecualikan untuk semua user (diatur admin)."""
    return list(load_settings()["monitoring"].get("excluded_profiles", []))


def set_global_excluded_profiles(profiles):
    """Ubah daftar profile global yang dikecualikan."""
    settings = load_settings()
    settings["monitoring"]["excluded_profiles"] = _clean_profiles(profiles)
    save_settings(settings)


def _clean_profiles(profiles):
    """Normalisasi daftar profile: trim, buang kosong & duplikat (tanpa beda huruf besar/kecil)."""
    if isinstance(profiles, str):
        profiles = profiles.split(",")
    result = []
    for item in profiles or []:
        name = str(item).strip()
        if name and name.lower() not in {p.lower() for p in result}:
            result.append(name)
    return result


def alert_level(down_count, config):
    """0 = normal, 1 = Warning ⚠️, 2 = Warning 🚨."""
    if down_count >= int(config["critical_threshold"]):
        return 2
    if down_count >= int(config["warning_threshold"]):
        return 1
    return 0


ALERT_LABELS = {
    1: "*Warning* ⚠️ Harap segera dicek lebih lanjut! /why",
    2: "*Warning* 🚨 Kritis, harap segera dicek! /why",
}


def get_monitoring_config(user_record):
    """Effective monitoring config for one user.

    Numbers: user value overrides the global default.
    excluded_profiles: global admin list + the user's own extra profiles.
    """
    global_monitoring = load_settings()["monitoring"]
    user_monitoring = user_record.get("monitoring", {}) or {}
    config = global_monitoring.copy()
    config.update({k: v for k, v in user_monitoring.items() if k not in {"excluded_profiles", "quiet_hours"}})
    # Keep values safe when reading records created by older bot versions.
    config.pop("notify_down_threshold", None)  # removed in 2.3.0; stage ⚠️ is the trigger now
    for key in ("warning_threshold", "critical_threshold"):
        try:
            config[key] = max(1, int(config[key]))
        except (KeyError, TypeError, ValueError):
            config[key] = DEFAULT_SETTINGS["monitoring"][key]
    if config["critical_threshold"] <= config["warning_threshold"]:
        config["critical_threshold"] = config["warning_threshold"] + 1
    global_profiles = _clean_profiles(global_monitoring.get("excluded_profiles", []))
    user_profiles = _clean_profiles(user_monitoring.get("excluded_profiles", []))
    config["global_excluded_profiles"] = global_profiles
    config["user_excluded_profiles"] = [p for p in user_profiles
                                        if p.lower() not in {g.lower() for g in global_profiles}]
    config["excluded_profiles"] = global_profiles + config["user_excluded_profiles"]
    config["quiet_hours"] = _clean_quiet_hours(user_monitoring.get("quiet_hours"))
    return config


# ---------------------------------------------------------------- quiet hours (per user)
def _minutes(text):
    """'HH:MM' (24 jam) -> menit sejak 00:00; ValueError bila tidak valid."""
    hours, minutes = str(text).strip().replace(".", ":").split(":")
    hours, minutes = int(hours), int(minutes)
    if not (0 <= hours <= 23 and 0 <= minutes <= 59):
        raise ValueError
    return hours * 60 + minutes


def parse_quiet_hours(text):
    """Teks '22:00-06:00' -> {'start': '22:00', 'end': '06:00'}; '-' -> None; ValueError bila salah."""
    text = str(text).strip()
    if text in {"-", "0", "off"}:
        return None
    try:
        start, end = [part.strip() for part in text.replace("–", "-").split("-")]
        start_min, end_min = _minutes(start), _minutes(end)
    except ValueError:
        raise ValueError("Format jam senyap: `HH:MM-HH:MM` (24 jam), contoh `22:00-06:00`.")
    if start_min == end_min:
        raise ValueError("Jam mulai dan selesai tidak boleh sama.")
    return {"start": f"{start_min // 60:02d}:{start_min % 60:02d}",
            "end": f"{end_min // 60:02d}:{end_min % 60:02d}"}


def _clean_quiet_hours(value):
    """Jam senyap tersimpan yang valid, atau None (data lama/rusak = nonaktif)."""
    if not isinstance(value, dict):
        return None
    try:
        return parse_quiet_hours(f"{value['start']}-{value['end']}")
    except (KeyError, ValueError):
        return None


def in_quiet_hours(quiet, now):
    """True bila waktu `now` (datetime) berada di jam senyap [start, end); mendukung lewat tengah malam."""
    if not quiet:
        return False
    start, end = _minutes(quiet["start"]), _minutes(quiet["end"])
    current = now.hour * 60 + now.minute
    if start < end:
        return start <= current < end
    return current >= start or current < end


def quiet_hours_label(quiet):
    """Teks jam senyap untuk tampilan."""
    return f"{quiet['start']}–{quiet['end']}" if quiet else "nonaktif"
