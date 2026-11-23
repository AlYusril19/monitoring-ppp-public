"""Automatic PPPoE monitoring job (runs every 60 s, see main.py).

Per user: skip if archived/paused, inside the user's quiet hours (no check, no
message, no charge; checking resumes when the quiet hours end), or not due yet
(normal_interval_minutes).
Per server, by alert level (0 normal, 1 = ⚠️ warning_threshold, 2 = 🚨 critical_threshold):
  * level ≥ 1 and no open alert window  → notify + charge "notify", open window
  * level rises inside the window (⚠️→🚨) → escalation notify, free
  * same/lower level inside the window   → quiet
  * window (alert_interval_minutes) over, still ≥ 1 → new charged notify
  * level 0 after an alert               → recovery message, reset
A router that cannot be reached (down, timeout, wrong login, API off) is
reported once with a friendly reason and is never charged; a message follows
when it is reachable again.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import pytz

from configs.app_settings import ALERT_LABELS, alert_level, get_monitoring_config, in_quiet_hours
from configs import chat_tracker
from configs.billing import charge_user
from configs.data_json_user import DATA_LOCK, load_user_data, save_user_data
from configs.format_rupiah import format_rupiah
from configs.mikrotik_function import RouterError, connect_router, get_down_users, router_error_text
from configs.navigation import home_keyboard, session_action_keyboard, topup_keyboard
from configs.send_message import bot_log, chat_log, escape_md, send_down_report, send_message

TIMEZONE = pytz.timezone('Asia/Jakarta')
USER_WORKERS = 8  # users checked at the same time by one job run
_user_pool = ThreadPoolExecutor(max_workers=USER_WORKERS, thread_name_prefix="monitor")


def _save_monitoring_state(user_id, state):
    """Write only this user's monitoring_state onto fresh data.

    The job reads datauser.json once at the start. Saving that whole snapshot
    later would undo changes made meanwhile (e.g. the notify charge made by
    charge_user, a topup approval, or a server edit).
    """
    with DATA_LOCK:
        users = load_user_data()
        record = users.get(str(user_id))
        if record is not None:
            # A ⏸ Jeda pressed while this check was running must not be undone by the job's snapshot.
            if record.get("monitoring_state", {}).get("paused"):
                state["paused"] = True
            record["monitoring_state"] = state
            save_user_data(users)


def _parse(text):
    """Ubah teks 'YYYY-mm-dd HH:MM:SS' menjadi datetime WIB."""
    return TIMEZONE.localize(datetime.strptime(text, '%Y-%m-%d %H:%M:%S'))


def _save_state_flags(user_id, state):
    """Hitung ulang alert_active user lalu simpan monitoring_state."""
    state["alert_active"] = any(item.get("alert_stage") for item in state.get("servers", {}).values())
    _save_monitoring_state(user_id, state)


def _safe_send(bot, chat_id, text, reply_markup=None):
    """Kirim pesan tanpa menghentikan job bila gagal (mis. user memblokir bot)."""
    try:
        send_message(bot, chat_id, text, reply_markup=reply_markup)
    except Exception as exc:
        print(f"Gagal kirim pesan monitoring ke {chat_id}: {exc}")


def check_client_status_and_notify(context):
    """Job tiap 60 detik: cek semua server user yang jatuh tempo dan kirim notifikasi 2 tahap.

    Users are checked in parallel (USER_WORKERS threads), so a router that times
    out never delays the other users' checks; the job waits for all of them.
    """
    bot = context.bot
    now = datetime.now(TIMEZONE)
    now_text = now.strftime('%Y-%m-%d %H:%M:%S')
    users = list(load_user_data().items())
    if chat_tracker.SYNCHRONOUS:
        for user_id, data in users:
            _check_user(bot, int(user_id), data, now, now_text)
        return
    futures = [_user_pool.submit(_check_user, bot, int(user_id), data, now, now_text) for user_id, data in users]
    for future in futures:
        try:
            future.result()
        except Exception as exc:
            print(f"Monitoring gagal untuk satu user: {exc}")


def _check_user(bot, user_id, data, now, now_text):
    """Cek semua server satu user (dipanggil paralel oleh job)."""
    user_id = int(user_id)
    state = data.setdefault("monitoring_state", {})
    if state.get("paused") or not data.get("aktif", True):
        # Archived users are neither monitored nor charged.
        return
    config = get_monitoring_config(data)
    if in_quiet_hours(config.get("quiet_hours"), now):
        # Quiet hours: no technician on duty, so nothing is checked, sent or charged.
        return
    # Always the normal interval, so a ⚠️ → 🚨 rise is noticed during an alert.
    interval = int(config["normal_interval_minutes"])
    alert_window = timedelta(minutes=int(config["alert_interval_minutes"]))
    last_check = state.get("last_check_at")
    if last_check:
        try:
            if now - _parse(last_check) < timedelta(minutes=interval):
                return
        except ValueError:
            pass
    state["last_check_at"] = now_text
    _save_monitoring_state(user_id, state)
    username_telegram = escape_md(data.get("username_telegram") or user_id)

    for server in data.get("servers", []):
        nama_server = server.get("name", server.get("ip", "-"))
        server_state = state.setdefault("servers", {}).setdefault(nama_server, {})
        try:
            connection = connect_router(server["ip"], server["username"], server["password"])
            down_users = get_down_users(connection, config.get("excluded_profiles"))
        except RouterError as exc:
            # Router down / unreachable: tell the user once, never charge.
            print(f"Monitoring {user_id}/{nama_server} gagal terhubung: {exc.detail or exc.kind}")
            if not server_state.get("error_notified"):
                _safe_send(bot, user_id,
                           f"🚨 *Server tidak dapat dihubungi* · 🕒 {now_text}\n"
                           f"{router_error_text(exc, nama_server, server.get('ip'))}\n\n"
                           "Harap cek kondisi router di lokasi. Monitoring tetap mencoba setiap "
                           f"{interval} menit dan memberi tahu saat terhubung kembali.\n"
                           "💰 Saldo tidak dipotong selama server tidak dapat dihubungi.",
                           reply_markup=home_keyboard())
                _safe_send(bot_log, chat_log, f"user *{username_telegram}* server *{escape_md(nama_server)}* "
                                              f"tidak dapat dihubungi ({exc.kind})")
                server_state["error_notified"] = True
                server_state["error_since"] = now_text
                _save_monitoring_state(user_id, state)
            continue
        if server_state.pop("error_notified", None):
            since = server_state.pop("error_since", None)
            _safe_send(bot, user_id, f"✅ Server *{escape_md(nama_server)}* kembali terhubung"
                                     + (f" (tidak terhubung sejak {since})." if since else ".")
                                     + " Monitoring berjalan normal.")
            _save_monitoring_state(user_id, state)
        level = alert_level(len(down_users), config)
        # Records from older versions only have alert_active.
        stage = int(server_state.get("alert_stage", 1 if server_state.get("alert_active") else 0))

        if level == 0:
            if stage:
                _safe_send(bot, user_id, f"✅ Status PPPoE di *{escape_md(nama_server)}* sudah pulih "
                                         f"({len(down_users)} down, di bawah ambang ⚠️).")
            for key in ("alert_stage", "alert_active", "alert_window_start"):
                server_state.pop(key, None)
            _save_state_flags(user_id, state)
            continue

        window_start = server_state.get("alert_window_start") or server_state.get("last_alert_at")
        window_open = False
        if stage and window_start:
            try:
                window_open = now - _parse(window_start) < alert_window
            except ValueError:
                window_open = False

        if window_open and level <= stage:
            continue  # already notified for this level; wait for the alert delay

        if window_open:
            # Escalation ⚠️ → 🚨 inside the alert delay: free.
            cost, remaining, title = 0, None, "🚨 Eskalasi"
        else:
            success, cost, remaining = charge_user(user_id, "notify")
            if not success:
                _safe_send(bot, user_id, "Saldo tidak cukup untuk notifikasi monitoring. Monitoring dihentikan "
                                         "sementara; lanjutkan dari ⚙️ Monitoring setelah topup.",
                           reply_markup=topup_keyboard())
                state["paused"] = True
                _save_monitoring_state(user_id, state)
                break  # monitoring paused: stop checking this user's other servers
            server_state["alert_window_start"] = now_text
            title = "Notifikasi otomatis" if not stage else "Pengingat (masih down)"

        # Save before sending so a failed message never causes a second charge.
        server_state["alert_stage"] = level
        server_state["alert_active"] = True
        server_state["last_alert_at"] = now_text
        _save_state_flags(user_id, state)

        cost_text = f"Biaya notifikasi: Rp{cost}" if cost else "Tanpa biaya (masih dalam jeda alert)."
        header = f"🔔 *{title}* · *{escape_md(nama_server)}*\n🕒 {now_text}"
        footer = (f"{ALERT_LABELS[level]}\n{cost_text}\nNotifikasi berikutnya: saat naik ke 🚨, atau setelah "
                  f"{config['alert_interval_minutes']} menit bila masih down.")
        try:
            # One message; a very long list is attached as a .txt file.
            send_down_report(bot, user_id, header, down_users, footer, reply_markup=session_action_keyboard())
        except Exception as exc:
            print(f"Gagal kirim notifikasi ke {user_id}: {exc}")
        sisa = format_rupiah(remaining) if remaining is not None else "-"
        _safe_send(bot_log, chat_log, f"user *{username_telegram}* {title} *{escape_md(nama_server)}*\n"
                                      f"User Down *({len(down_users)} Users)*\n{ALERT_LABELS[level]}\n"
                                      f"Biaya Rp{cost} · Sisa saldo User {sisa}")
